import time
import json
import logging
from typing import Callable

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response as DRFResponse
from common.response import ApiResponse


class APILoggingMiddleware(MiddlewareMixin):
    """Lightweight API request/response logger.

    - Logs method, path, status, duration, user id (if any)
    - Controlled by settings or env:
      - API_LOG (default: True)
      - API_LOG_BODY (default: False) — if True, logs small JSON bodies (<= 2KB)
    """

    def __init__(self, get_response: Callable | None = None) -> None:
        super().__init__(get_response)
        self.logger = logging.getLogger(__name__)
        self.enabled: bool = getattr(settings, "API_LOG", True)
        self.log_body: bool = getattr(settings, "API_LOG_BODY", False)
        self.max_body_bytes: int = getattr(settings, "API_LOG_MAX_BODY", 2048)

    def process_request(self, request: HttpRequest):
        if not self.enabled:
            return None
        request._api_log_ts = time.monotonic()
        # Best-effort to capture small JSON body without consuming stream
        request._api_log_body = None
        if self.log_body and request.method in ("POST", "PUT", "PATCH"):
            try:
                if request.body and len(request.body) <= self.max_body_bytes:
                    request._api_log_body = request.body.decode("utf-8", errors="ignore")
            except Exception:
                request._api_log_body = None
        return None

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        if not self.enabled:
            return response
        start = getattr(request, "_api_log_ts", None)
        duration_ms = None
        if start is not None:
            try:
                duration_ms = int((time.monotonic() - start) * 1000)
            except Exception:
                duration_ms = None

        user_id = None
        try:
            if getattr(request, "user", None) and request.user.is_authenticated:
                user_id = str(getattr(request.user, "id", None))
        except Exception:
            user_id = None

        log_record = {
            "method": request.method,
            "path": request.get_full_path(),
            "status": getattr(response, "status_code", None),
            "duration_ms": duration_ms,
            "user_id": user_id,
        }

        if self.log_body and getattr(request, "_api_log_body", None):
            log_record["req_body"] = request._api_log_body

        # Avoid dumping large responses; only lengths
        try:
            content_length = int(response.get("Content-Length")) if response.get("Content-Length") else None
        except Exception:
            content_length = None
        log_record["resp_len"] = content_length

        self.logger.info("api", extra={"payload": log_record})
        return response


class GlobalExceptionMiddleware(MiddlewareMixin):
    """Catch-all exception handler to log and standardize error responses.

    - Logs exception with path, method, user_id
    - Returns ApiResponse.error with 500 by default (or preserves DRF response if already built)
    """

    def __init__(self, get_response: Callable | None = None) -> None:
        super().__init__(get_response)
        self.logger = logging.getLogger(__name__)

    def process_exception(self, request: HttpRequest, exception: Exception):
        try:
            user_id = None
            if getattr(request, "user", None) and request.user.is_authenticated:
                user_id = str(getattr(request.user, "id", None))
            self.logger.exception(
                "unhandled_exception",
                extra={
                    "payload": {
                        "method": request.method,
                        "path": request.get_full_path(),
                        "user_id": user_id,
                        "class": exception.__class__.__name__,
                    }
                },
            )
        except Exception:
            # Avoid cascading failures in exception handling
            pass

        # Standardized error response - use basic HttpResponse to avoid rendering issues
        from django.http import JsonResponse
        return JsonResponse({
            "succeed": False,
            "errorMessage": "Internal server error",
            "errorCode": "INTERNAL_ERROR",
            "data": {"detail": str(exception)}
        }, status=500)


class ApiResponseEnvelopeMiddleware(MiddlewareMixin):
    """Ensure all DRF Responses conform to unified ApiResponse envelope.

    - For 2xx: wraps as ApiResponse.success(data=<original>)
    - For 4xx/5xx (already handled by GlobalExceptionMiddleware for 5xx): wraps as ApiResponse.error
    - If already in unified format (contains 'succeed' key), leave unchanged
    """

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        # First, best-effort render any renderable response to avoid ContentNotRenderedError downstream
        try:
            if hasattr(response, 'render') and callable(getattr(response, 'render')) and not getattr(response, 'is_rendered', False):
                response.render()
        except Exception:
            # Do not fail the pipeline if rendering here throws
            pass

        # Only wrap DRF Response; non-DRF keep 原样
        if not isinstance(response, DRFResponse):
            return response

        body = getattr(response, 'data', None)
        if isinstance(body, dict) and 'succeed' in body:
            try:
                response.render()
            except Exception:
                pass
            return response

        try:
            # Success
            if 200 <= int(response.status_code) < 400:
                resp = ApiResponse.success(data=body, status_code=response.status_code)
                try:
                    resp.render()
                except Exception:
                    pass
                return resp
            # Client error
            else:
                # Prefer 'detail' field as message when present
                message = None
                if isinstance(body, dict):
                    message = body.get('message') or body.get('detail') or body.get('error')
                if not message:
                    message = 'Request failed'
                resp = ApiResponse.error(error_message=message, status_code=response.status_code, data=body)
                try:
                    resp.render()
                except Exception:
                    pass
                return resp
        except Exception:
            # On any failure, return original response to avoid masking issues
            try:
                response.render()
            except Exception:
                pass
            return response


class FinalizeRenderMiddleware(MiddlewareMixin):
    """Ensure any renderable response is rendered immediately after envelope processing.

    Prevents ContentNotRenderedError by rendering DRF responses before CommonMiddleware.
    """

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        logger = logging.getLogger(__name__)
        
        # Log response details for debugging
        debug_info = {
            "path": request.get_full_path(),
            "resp_type": response.__class__.__name__,
            "has_render": hasattr(response, 'render'),
            "is_rendered": getattr(response, 'is_rendered', 'no_attr'),
            "has_data": hasattr(response, 'data'),
            "status_code": getattr(response, 'status_code', 'no_attr'),
            "has_accepted_renderer": hasattr(response, 'accepted_renderer'),
            "accepted_renderer": getattr(response, 'accepted_renderer', 'no_attr'),
            "has_content": hasattr(response, 'content'),
            "content_type": response.get('Content-Type', 'no_content_type') if hasattr(response, 'get') else 'no_get_method'
        }
        
        logger.info("finalize_response_check", extra={"payload": debug_info})
        
        # Check if this is a DRF Response that needs rendering
        has_render_method = hasattr(response, 'render') and callable(getattr(response, 'render'))
        is_already_rendered = getattr(response, 'is_rendered', False)
        needs_render = has_render_method and not is_already_rendered
        
        # Also handle responses that have render method but might be in a bad state
        if has_render_method:
            logger.info("finalize_render_start", extra={"payload": {"path": request.get_full_path(), "resp_type": response.__class__.__name__}})
            
            try:
                # Ensure the response has a renderer; if not, set a default one
                if hasattr(response, 'accepted_renderer') and not response.accepted_renderer:
                    from rest_framework.renderers import JSONRenderer
                    response.accepted_renderer = JSONRenderer()
                    response.accepted_media_type = 'application/json'
                    response.renderer_context = {'request': request, 'response': response, 'view': None}
                
                # Force render the response - even if it claims to be rendered, it might not be properly rendered
                if not is_already_rendered:
                    response.render()
                    logger.info("finalize_render_done", extra={"payload": {"path": request.get_full_path(), "rendered": True}})
                else:
                    # Response claims to be rendered but might still cause ContentNotRenderedError
                    # Force render anyway as a safety measure
                    logger.info("finalize_render_force", extra={"payload": {"path": request.get_full_path(), "force_render": True}})
                    try:
                        response.render()
                        logger.info("finalize_render_force_success", extra={"payload": {"path": request.get_full_path()}})
                    except Exception as force_error:
                        logger.warning("finalize_render_force_failed", extra={"payload": {"path": request.get_full_path(), "error": str(force_error)}})
                
            except Exception as e:
                # Last resort: convert to JsonResponse to prevent ContentNotRenderedError
                logger.warning("finalize_render_error", extra={"payload": {"path": request.get_full_path(), "error": str(e)}})
                
                if hasattr(response, 'data') and hasattr(response, 'status_code'):
                    from django.http import JsonResponse
                    try:
                        # Try to extract data from the DRF Response
                        data = response.data
                        status_code = response.status_code
                        response = JsonResponse(data, status=status_code, safe=False)
                        logger.info("converted_to_jsonresponse", extra={"payload": {"path": request.get_full_path()}})
                    except Exception as convert_error:
                        logger.error("conversion_failed", extra={"payload": {"path": request.get_full_path(), "error": str(convert_error)}})
                        # Ultimate fallback - return a basic error response
                        response = JsonResponse({"succeed": False, "errorMessage": "Response rendering failed"}, status=500)

        # Additional safety: if this is still a DRF response that might cause issues, convert it
        if has_render_method and hasattr(response, 'data') and hasattr(response, 'status_code'):
            from django.http import JsonResponse
            try:
                logger.info("safety_conversion_attempt", extra={"payload": {"path": request.get_full_path(), "resp_type": response.__class__.__name__}})
                data = response.data
                status_code = response.status_code
                response = JsonResponse(data, status=status_code, safe=False)
                logger.info("safety_conversion_success", extra={"payload": {"path": request.get_full_path()}})
            except Exception as safety_error:
                logger.warning("safety_conversion_failed", extra={"payload": {"path": request.get_full_path(), "error": str(safety_error)}})
                        
        return response


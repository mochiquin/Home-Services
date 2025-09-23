"""
Standardized API response format for all endpoints.
"""
from rest_framework import status
from rest_framework.response import Response
from typing import Any, Optional, Dict


class ApiResponse:
    """
    Standardized API response format.
    
    Format:
    {
        "succeed": boolean,
        "errorMessage": string (optional),
        "errorCode": string (optional), 
        "message": string (optional),
        "data": any (optional)
    }
    """
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = None,
        status_code: int = status.HTTP_200_OK
    ) -> Response:
        """
        Create a successful response.
        
        Args:
            data: Response data
            message: Success message
            status_code: HTTP status code
            
        Returns:
            Response object
        """
        response_data = {
            "succeed": True,
            "message": message
        }
        
        if data is not None:
            response_data["data"] = data
            
        return Response(response_data, status=status_code)
    
    @staticmethod
    def error(
        error_message: str,
        error_code: str = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        data: Any = None
    ) -> Response:
        """
        Create an error response.
        
        Args:
            error_message: Error message
            error_code: Error code (optional)
            status_code: HTTP status code
            data: Additional error data (optional)
            
        Returns:
            Response object
        """
        response_data = {
            "succeed": False,
            "errorMessage": error_message
        }
        
        if error_code:
            response_data["errorCode"] = error_code
            
        if data is not None:
            response_data["data"] = data
            
        return Response(response_data, status=status_code)
    
    @staticmethod
    def created(
        data: Any = None,
        message: str = "Created successfully"
    ) -> Response:
        """
        Create a 201 Created response.
        
        Args:
            data: Response data
            message: Success message
            
        Returns:
            Response object
        """
        return ApiResponse.success(data=data, message=message, status_code=status.HTTP_201_CREATED)
    
    @staticmethod
    def unauthorized(
        error_message: str = "Authentication required",
        error_code: str = "UNAUTHORIZED"
    ) -> Response:
        """
        Create a 401 Unauthorized response.
        
        Args:
            error_message: Error message
            error_code: Error code
            
        Returns:
            Response object
        """
        return ApiResponse.error(
            error_message=error_message,
            error_code=error_code,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    @staticmethod
    def forbidden(
        error_message: str = "Access forbidden",
        error_code: str = "FORBIDDEN"
    ) -> Response:
        """
        Create a 403 Forbidden response.
        
        Args:
            error_message: Error message
            error_code: Error code
            
        Returns:
            Response object
        """
        return ApiResponse.error(
            error_message=error_message,
            error_code=error_code,
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    @staticmethod
    def not_found(
        error_message: str = "Resource not found",
        error_code: str = "NOT_FOUND"
    ) -> Response:
        """
        Create a 404 Not Found response.
        
        Args:
            error_message: Error message
            error_code: Error code
            
        Returns:
            Response object
        """
        return ApiResponse.error(
            error_message=error_message,
            error_code=error_code,
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    @staticmethod
    def internal_error(
        error_message: str = "Internal server error",
        error_code: str = "INTERNAL_ERROR"
    ) -> Response:
        """
        Create a 500 Internal Server Error response.
        
        Args:
            error_message: Error message
            error_code: Error code
            
        Returns:
            Response object
        """
        return ApiResponse.error(
            error_message=error_message,
            error_code=error_code,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

from enum import Enum
from django.db import models


class FunctionalRole(models.TextChoices):
    """
    Functional roles for contributors in MC-STC analysis.
    MVP version with simplified classification.
    """
    CODER = 'coder', 'Coder'
    REVIEWER = 'reviewer', 'Reviewer' 
    UNCLASSIFIED = 'unclassified', 'Unclassified'

    @classmethod
    def get_choices_dict(cls):
        """Return choices as a dictionary for API responses."""
        return [
            {'value': choice[0], 'label': choice[1]}
            for choice in cls.choices
        ]

    @classmethod
    def get_default_role(cls):
        """Get default role for new contributors."""
        return cls.UNCLASSIFIED

    @classmethod
    def is_valid_role(cls, role):
        """Check if a role value is valid."""
        return role in [choice[0] for choice in cls.choices]


class ActivityLevel(Enum):
    """Activity level classification based on modification count."""
    HIGH = 'high'       # >= 1000 modifications
    MEDIUM = 'medium'   # 100-999 modifications  
    LOW = 'low'         # 10-99 modifications
    MINIMAL = 'minimal' # < 10 modifications

    @classmethod
    def get_level(cls, total_modifications):
        """Determine activity level based on modification count."""
        if total_modifications >= 1000:
            return cls.HIGH
        elif total_modifications >= 100:
            return cls.MEDIUM
        elif total_modifications >= 10:
            return cls.LOW
        else:
            return cls.MINIMAL

    @classmethod
    def get_choices_dict(cls):
        """Return activity level choices for API responses."""
        return [
            {'value': level.value, 'label': level.value.title()}
            for level in cls
        ]


class RoleConfidenceLevel(Enum):
    """Confidence levels for role classification."""
    HIGH = 0.8      # Very confident in role suggestion
    MEDIUM = 0.6    # Moderately confident
    LOW = 0.4       # Low confidence
    MINIMAL = 0.2   # Very low confidence

    @classmethod
    def get_confidence_for_stats(cls, total_mods, files_count, avg_mods):
        """Calculate confidence level based on contributor statistics."""
        # More data = higher confidence
        if total_mods >= 100 and files_count >= 10:
            return cls.HIGH.value
        elif total_mods >= 50 and files_count >= 5:
            return cls.MEDIUM.value
        elif total_mods >= 10:
            return cls.LOW.value
        else:
            return cls.MINIMAL.value

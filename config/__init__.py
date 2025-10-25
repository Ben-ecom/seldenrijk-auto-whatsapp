"""
Configuration package for WhatsApp Recruitment Platform.

This package contains configuration files and registries used throughout the application.
"""

from .tag_registry import (
    ALL_LABELS,
    get_label_title,
    LEAD_QUALITY_MAP,
    BEHAVIOR_MAP,
    JOURNEY_MAP
)

__all__ = [
    'ALL_LABELS',
    'get_label_title',
    'LEAD_QUALITY_MAP',
    'BEHAVIOR_MAP',
    'JOURNEY_MAP'
]

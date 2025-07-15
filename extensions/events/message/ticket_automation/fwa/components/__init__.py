# extensions/events/message/ticket_automation/fwa/components/__init__.py
"""
FWA-specific component templates and builders.
"""

from .fwa_templates import (
    WAR_WEIGHT_REQUEST_TEMPLATE,
    FWA_EXPLANATION_TEMPLATE,
    LAZY_CWL_TEMPLATE,
    AGREEMENT_TEMPLATE,
    FWA_COMPLETION_TEMPLATE
)

__all__ = [
    'WAR_WEIGHT_REQUEST_TEMPLATE',
    'FWA_EXPLANATION_TEMPLATE',
    'LAZY_CWL_TEMPLATE',
    'AGREEMENT_TEMPLATE',
    'FWA_COMPLETION_TEMPLATE'
]
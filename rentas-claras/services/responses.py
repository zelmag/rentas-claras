"""
Response Helpers
=================

Standardized JSON response helpers for API endpoints.
Reduces repetitive code across routes.
"""

from flask import jsonify
from typing import Any, Dict, Optional


def success_response(data: Optional[Dict[str, Any]] = None, message: Optional[str] = None):
    """
    Create a standardized success response.
    
    Args:
        data: Optional dict of additional data to include
        message: Optional success message
        
    Returns:
        Flask JSON response with 200 status
        
    Example:
        return success_response({"tenant_id": "MAT-A"})
        # Returns: {"success": True, "tenant_id": "MAT-A"}
    """
    response = {"success": True}
    
    if message:
        response["message"] = message
        
    if data:
        response.update(data)
        
    return jsonify(response)


def error_response(error: str, status_code: int = 400, details: Optional[Dict[str, Any]] = None):
    """
    Create a standardized error response.
    
    Args:
        error: Error message to display
        status_code: HTTP status code (default 400)
        details: Optional dict of additional error details
        
    Returns:
        Tuple of (Flask JSON response, status_code)
        
    Example:
        return error_response("tenant_id is required")
        # Returns: ({"success": False, "error": "tenant_id is required"}, 400)
    """
    response = {
        "success": False,
        "error": error
    }
    
    if details:
        response["details"] = details
        
    return jsonify(response), status_code


def not_found_response(resource: str = "Resource"):
    """
    Create a standardized 404 not found response.
    
    Args:
        resource: Name of the resource that wasn't found
        
    Returns:
        Tuple of (Flask JSON response, 404)
    """
    return error_response(f"{resource} not found", status_code=404)


def validation_error_response(errors: list):
    """
    Create a response for validation errors.
    
    Args:
        errors: List of validation error messages
        
    Returns:
        Tuple of (Flask JSON response, 400)
    """
    return error_response(
        error="; ".join(errors) if isinstance(errors, list) else str(errors),
        status_code=400
    )


def server_error_response(error: str = "Internal server error"):
    """
    Create a standardized 500 server error response.
    
    Args:
        error: Error message
        
    Returns:
        Tuple of (Flask JSON response, 500)
    """
    return error_response(error, status_code=500)

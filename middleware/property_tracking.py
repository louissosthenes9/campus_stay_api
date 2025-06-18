
from django.utils import timezone
from django.db import models
from properties.models import Properties
import logging

logger = logging.getLogger(__name__)

class PropertyViewTrackingMiddleware:
    """Middleware to automatically track property views."""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.process_request(request)
        return response

    def process_request(self, request):
        response = self.get_response(request)
        
        # Check if this is a property detail view
        if (request.method == 'GET' and 
            '/api/v1/properties/' in request.path and 
            request.path.endswith('/') and
            request.path.count('/') == 4): 
            
            try:
                # Extract property ID from URL
                path_parts = request.path.strip('/').split('/')
                if len(path_parts) >= 3 and path_parts[2].isdigit():
                    property_id = int(path_parts[2])
                    
                    # Update view tracking
                    Properties.objects.filter(id=property_id).update(
                        view_count=models.F('view_count') + 1,
                        last_viewed=timezone.now()
                    )
                    
                    # Track in session for recently viewed
                    if 'recently_viewed_properties' not in request.session:
                        request.session['recently_viewed_properties'] = []
                    
                    viewed_properties = request.session['recently_viewed_properties']
                    
                    # Remove if already exists
                    if property_id in viewed_properties:
                        viewed_properties.remove(property_id)
                    
                    # Add to beginning
                    viewed_properties.insert(0, property_id)
                    
                    # Keep only last 20
                    request.session['recently_viewed_properties'] = viewed_properties[:20]
                    request.session.modified = True
                    
                    logger.info(f"Property {property_id} view tracked automatically")
                    
            except (ValueError, IndexError, Exception) as e:
                logger.error(f"Error in property view tracking middleware: {str(e)}")
        
        return response
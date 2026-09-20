from urllib import request

from rest_framework.permissions import BasePermission


class IsOrganizer(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == 'organizer'
        )


class IsVenueOwner(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == 'venue_owner'
        )

class IsVenueOwnerObjectOwner(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and (
                request.method in ['GET', 'HEAD', 'OPTIONS']
                or request.user.role == 'venue_owner'
            )
        )

    def has_object_permission(self, request, view, obj):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        owner = obj.owner if hasattr(obj, 'owner') else obj.venue.owner

        return (
            request.user.role == 'venue_owner'
            and owner == request.user
        )
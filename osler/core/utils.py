import os
import uuid
import string

from django.db.models import Q
from django.conf import settings
from django.shortcuts import get_object_or_404

from . import models


def make_filepath(instance, filename):
    """Produces a unique file path for the upload_to of a FileField.

    This is important because any URL is 1) transmitted unencrypted and
    2) automatically referred to any libraries we include (i.e. Bootstrap).

    The produced path is of the form:
    "[model name]/[field name]/[random name].[filename extension]".

    Inspired by https://djangosnippets.org/snippets/2819/, modified over
    the years.
    """

    carry_on = True
    while carry_on:
        new_filename = "%s.%s" % (uuid.uuid4(), filename.split('.')[-1])

        path = new_filename

        # if the file already exists, try again to generate a new filename
        carry_on = os.path.isfile(os.path.join(settings.MEDIA_ROOT, path))

    return path


def all_variations(name):
    """all_variations is a function that is used to help search for all
    variations of a string that have either added, removed, or changed
    1 letter. Function returns a list of all variations of the input string.
    """
    all_vars = []
    if name is None or len(name) == 0:
        return all_vars
    if len(name) == 1:
        all_vars.append(name)
        return all_vars
    else:
        # try all variations of switching letters, other than first letter
        for i in range(1, len(name)):
            # remove letter
            all_vars.append(name[:i] + name[i + 1:])
            # change letter and add letter
            for j in string.ascii_lowercase:
                all_vars.append(name[:i] + j + name[i + 1:])
                all_vars.append(name[:i] + j + name[i:])

        all_vars.append(name)
        return all_vars


def return_duplicates(first_name_str, last_name_str):
    """search database for all variations of first and last name off by 1
    letter (except for first letter must be correct) and return matching
    results.  First name may also be abbreviated (to cover cases like
    ben and benjamin)
    """
    first_name_var = all_variations(first_name_str.capitalize())
    last_name_var = all_variations(last_name_str.capitalize())
    if len(first_name_var) == 0 or len(last_name_var) == 0:
        return

    return models.Patient.objects.filter(
        (Q(first_name__in=first_name_var) |
         Q(first_name__istartswith=first_name_str.capitalize())) &
        Q(last_name__in=last_name_var))


def get_names_from_url_query_dict(request):
    """Get first_name and last_name from a request object in a dict.
    """

    qs_dict = {param: request.GET[param] for param
               in ['first_name', 'last_name']
               if param in request.GET}

    return qs_dict


def get_due_date_from_url_query_dict(request):
    '''Get due date from request object in a dict'''

    qs_dict = {param: request.GET[param] for param
               in ['due_date']
               if param in request.GET}

    return qs_dict

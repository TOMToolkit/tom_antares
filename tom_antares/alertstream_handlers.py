"""
Functions to deal with targets after they are created from the Antares Stream
"""
import logging
from typing import Union
from django.conf import settings
from django.db.models.query import QuerySet

from tom_targets.models import Target, TargetName
from tom_targets.utils import cone_search_filter

from .antares import ANTARESBroker

logger = logging.getLogger(__name__)

try:
    CONE_SEARCH_RADIUS_ARCSEC = settings.CONE_SEARCH_RADIUS
except AttributeError:
    CONE_SEARCH_RADIUS_ARCSEC = 2.


def handle_alert(locus):
    """
    Ingests the locus into a new target object (or updates an existing one)
    """
    target_matches = cone_search_filter(Target.objects.all(), locus.ra, locus.dec, CONE_SEARCH_RADIUS_ARCSEC / 3600.)
    logger.info(f"Targets within {CONE_SEARCH_RADIUS_ARCSEC:.1f} arcsec: {target_matches}")
    
    broker = ANTARESBroker()
    alert = broker.alert_to_dict(locus)

    if target_matches.count():
        # then this target already exists in the Targets table
        target = target_matches.order_by("separation").first()
        logger.info(f"Found existing target matching this alert: {target.name}")
        created = False
        
        # update the TargetName objects returned to instead point to the existing target
        aliases = broker.aliases_from_locus(alert, target)
        
    else:
        # then this target does not exist, so we create it from scratch
        target, _, aliases = broker.to_target(alert)
        logger.info(f"No existing target found, adding {target.name} as new target")
        created = True
        
    broker.process_reduced_data(target, alert)

    # save the aliases that we found for this target
    logger.info(f"Adding {aliases} to {target}")
    aliases_added = []
    for alias in aliases:
        existing_alias = TargetName.objects.filter(name=alias.name)
        if not existing_alias.exists():
            alias.save()
            aliases_added.append(alias.name)
        elif existing_alias.exclude(target=target).exists():
            # this will happen if the alias exists under a different target
            # than the one we are trying to save it with
            # in which case we should log a warning
            logger.warning(
                f"The name alias {alias.name} exists under the target {existing_alias.first().target}, "
                f"which is different from the nearest target in the existing database (which is {target}). "
                "We are NOT re-assigning this alias!"
            )
    
    return target, created, aliases_added

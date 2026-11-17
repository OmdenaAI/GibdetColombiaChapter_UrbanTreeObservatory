import time

from django.contrib.gis.db.models import Extent, GeometryField
from django.contrib.gis.db.models.functions import Cast
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from tqdm import tqdm

from apps.biodiversity.models import BiodiversityRecord
from apps.places.models import Locality, Neighborhood


class Command(BaseCommand):
    help = "Fixes BiodiversityRecord instances assigned to the 'Desconocido' neighborhood by finding their correct neighborhoods using spatial queries."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the command without making any changes to the database",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Number of records to process in each batch (default: 500)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of records to process",
        )
        parser.add_argument(
            "--neighborhood-id",
            type=int,
            default=688,
            help="ID of the 'Desconocido' neighborhood (default: 688)",
        )
        parser.add_argument(
            "--stats-only",
            action="store_true",
            help="Only print stats without processing records",
        )
        parser.add_argument(
            "--all-records",
            action="store_true",
            help="Process all records, including those that have already been processed",
        )

    def _prepare_query(self, unknown_neighborhood_id, all_records):
        """Prepare the base query for records that need processing."""
        # Find all records with "Desconocido" neighborhood that need processing
        base_query = BiodiversityRecord.all_objects.filter(
            neighborhood_id=unknown_neighborhood_id,
            location__isnull=False,
        )

        # Unless all_records flag is set, only process records that haven't been processed yet
        # This addresses the halving issue by excluding records we've already processed
        if not all_records:
            base_query = base_query.filter(
                Q(system_comment__isnull=True) | Q(system_comment="")
            )

        return base_query

    def _get_filtered_boundaries(self, base_query, unknown_neighborhood_id):
        """Get neighborhoods and localities filtered by the records' extent."""
        # Get all neighborhoods with boundaries
        valid_neighborhoods = Neighborhood.objects.exclude(
            id=unknown_neighborhood_id
        ).exclude(boundary__isnull=True)

        self.stdout.write(
            f"Found {valid_neighborhoods.count()} neighborhoods with boundaries"
        )

        # Get all localities with boundaries
        valid_localities = Locality.objects.exclude(boundary__isnull=True)
        self.stdout.write(
            f"Found {valid_localities.count()} localities with boundaries"
        )

        # Get the extent of all records to filter neighborhoods
        extent = base_query.annotate(
            location_geom=Cast("location", GeometryField())
        ).aggregate(extent=Extent("location_geom"))["extent"]

        if extent:
            filtered_neighborhoods, filtered_localities = self._filter_by_extent(
                extent, valid_neighborhoods, valid_localities
            )
        else:
            filtered_neighborhoods = valid_neighborhoods
            filtered_localities = valid_localities
            self.stdout.write(
                "Could not determine extent, using all neighborhoods and localities"
            )

        return filtered_neighborhoods, filtered_localities

    def _filter_by_extent(self, extent, valid_neighborhoods, valid_localities):
        """Filter neighborhoods and localities by a geographic extent."""
        min_lon, min_lat, max_lon, max_lat = extent
        # Add a buffer for safety
        buffer = 0.05  # approximately 5km
        min_lon -= buffer
        min_lat -= buffer
        max_lon += buffer
        max_lat += buffer

        # Bounding box for the extent
        bbox = (
            f"POLYGON(("
            f"{min_lon} {min_lat}, "
            f"{max_lon} {min_lat}, "
            f"{max_lon} {max_lat}, "
            f"{min_lon} {max_lat}, "
            f"{min_lon} {min_lat}"
            f"))"
        )

        # Filter neighborhoods that intersect with the extent
        filtered_neighborhoods = valid_neighborhoods.filter(boundary__intersects=bbox)

        # Filter localities that intersect with the extent
        filtered_localities = valid_localities.filter(boundary__intersects=bbox)

        self.stdout.write(
            f"Filtered to {filtered_neighborhoods.count()} neighborhoods and "
            f"{filtered_localities.count()} localities within records extent"
        )

        return filtered_neighborhoods, filtered_localities

    def _process_record(
        self,
        record,
        filtered_neighborhoods,
        filtered_localities,
        unknown_neighborhood_cache,
        dry_run,
    ):
        """Process an individual record to find its neighborhood."""
        found_match = False  # noqa: F841
        record_result = {
            "found_match": False,
            "neighborhood": None,
            "system_comment": None,
            "updated_with_neighborhood": False,
            "updated_with_locality": False,
            "created_neighborhood": False,
        }

        # 1. First try to find a direct neighborhood match
        matching_neighborhoods = list(
            filtered_neighborhoods.filter(boundary__contains=record.location)
        )

        if matching_neighborhoods:
            # Take the first matching neighborhood
            record_result["neighborhood"] = matching_neighborhoods[0]
            record_result["system_comment"] = (
                f"Automatically assigned to neighborhood '{matching_neighborhoods[0].name}' "
                f"based on spatial location."
            )
            record_result["updated_with_neighborhood"] = True
            record_result["found_match"] = True
            return record_result

        # 2. If no neighborhood match, try to find a locality match
        matching_localities = list(
            filtered_localities.filter(boundary__contains=record.location)
        )

        if matching_localities:
            # Take the first matching locality
            locality = matching_localities[0]

            # Try to get a cached neighborhood or find/create a new one
            unknown_neighborhood, created = self._get_or_create_unknown_neighborhood(
                locality, unknown_neighborhood_cache, dry_run
            )

            if unknown_neighborhood:
                record_result["neighborhood"] = unknown_neighborhood
                record_result["system_comment"] = (
                    f"Automatically assigned to placeholder neighborhood '{unknown_neighborhood.name}' "
                    f"as record is within locality '{locality.name}' boundary but no matching "
                    f"neighborhood boundary was found."
                )
                record_result["updated_with_locality"] = True
                record_result["found_match"] = True
                record_result["created_neighborhood"] = created
                return record_result

        # No match found
        record_result["system_comment"] = (
            "No matching neighborhood or locality boundary found for this record."
        )

        return record_result

    def _get_or_create_unknown_neighborhood(
        self, locality, unknown_neighborhood_cache, dry_run
    ):
        """Get a cached unknown neighborhood or create a new one if needed."""
        created = False

        # Check if we already have a "Desconocido en X" neighborhood for this locality
        if locality.id in unknown_neighborhood_cache:
            unknown_neighborhood = unknown_neighborhood_cache[locality.id]
        else:
            # Try to find an existing "Desconocido en X" neighborhood
            unknown_neighborhood_name = f"Desconocido en {locality.name}"
            unknown_neighborhood = Neighborhood.objects.filter(
                name=unknown_neighborhood_name, locality=locality
            ).first()

            # Create a new "Desconocido en X" neighborhood if it doesn't exist
            if not unknown_neighborhood and not dry_run:
                unknown_neighborhood = Neighborhood.objects.create(
                    name=unknown_neighborhood_name,
                    locality=locality,
                    boundary=None,  # No boundary for these special neighborhoods
                )
                created = True
                self.stdout.write(
                    f"Created new neighborhood: {unknown_neighborhood_name}"
                )

            # Cache the neighborhood for future use
            unknown_neighborhood_cache[locality.id] = unknown_neighborhood

        return unknown_neighborhood, created

    def _bulk_update_records(self, records_to_update):
        """Perform a bulk update of records."""
        if records_to_update:
            BiodiversityRecord.all_objects.bulk_update(
                records_to_update, fields=["neighborhood", "system_comment"]
            )

    def _print_final_report(self, stats, elapsed_time, dry_run):
        """Print the final report with statistics."""
        self.stdout.write(
            self.style.SUCCESS(f"Processing complete in {elapsed_time:.2f} seconds:")
        )
        self.stdout.write(f"- Total records processed: {stats['processed_records']}")
        self.stdout.write(
            f"- Records assigned to existing neighborhoods: {stats['updated_with_neighborhood']}"
        )
        self.stdout.write(
            f"- Records assigned to locality-based placeholder neighborhoods: {stats['updated_with_locality']}"
        )
        self.stdout.write(
            f"- New placeholder neighborhoods created: {stats['created_neighborhoods']}"
        )
        self.stdout.write(
            f"- Records without matching neighborhood or locality: {stats['non_matching_records']}"
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "This was a dry run. No changes were made to the database."
                )
            )

    def _process_batch(  # noqa: C901
        self,
        batch_ids,
        filtered_neighborhoods,
        filtered_localities,
        unknown_neighborhood_cache,
        stats,
        dry_run,
    ):
        """Process a batch of records."""
        # Skip if batch is empty
        if not batch_ids:
            return 0

        # Fetch the full records for this batch
        batch_records = list(BiodiversityRecord.all_objects.filter(id__in=batch_ids))

        # Process each record in the batch
        neighborhood_updates = {}  # record_id -> neighborhood
        system_comment_updates = {}  # record_id -> comment

        for record in batch_records:
            result = self._process_record(
                record,
                filtered_neighborhoods,
                filtered_localities,
                unknown_neighborhood_cache,
                dry_run,
            )

            if result["neighborhood"]:
                neighborhood_updates[record.id] = result["neighborhood"]

            if result["system_comment"]:
                system_comment_updates[record.id] = result["system_comment"]

            # Update statistics
            if result["updated_with_neighborhood"]:
                stats["updated_with_neighborhood"] += 1
            if result["updated_with_locality"]:
                stats["updated_with_locality"] += 1
            if result["created_neighborhood"]:
                stats["created_neighborhoods"] += 1
            if not result["found_match"]:
                stats["non_matching_records"] += 1

        # Bulk update records with their new neighborhoods and comments
        if (neighborhood_updates or system_comment_updates) and not dry_run:
            with transaction.atomic():
                # Prepare records for bulk update
                records_to_update = []

                # First, load all affected records in a single query to reduce database hits
                affected_ids = set(neighborhood_updates.keys()) | set(
                    system_comment_updates.keys()
                )
                records_dict = {
                    record.id: record
                    for record in BiodiversityRecord.all_objects.filter(
                        id__in=affected_ids
                    )
                }

                # Update records with new neighborhoods
                for record_id, new_neighborhood in neighborhood_updates.items():
                    if record_id in records_dict:
                        record = records_dict[record_id]
                        record.neighborhood = new_neighborhood
                        record.system_comment = system_comment_updates.get(
                            record_id, ""
                        )
                        records_to_update.append(record)

                # Update records that have comments but no neighborhood updates
                comment_only_ids = set(system_comment_updates.keys()) - set(
                    neighborhood_updates.keys()
                )
                for record_id in comment_only_ids:
                    if record_id in records_dict:
                        record = records_dict[record_id]
                        record.system_comment = system_comment_updates[record_id]
                        records_to_update.append(record)

                # Perform the bulk update if there are records to update
                self._bulk_update_records(records_to_update)

        return len(batch_records)

    def handle(self, *args, **options):
        """Handle the command execution."""
        # Get command options
        dry_run = options.get("dry_run", False)
        batch_size = options.get("batch_size", 500)
        limit = options.get("limit")
        unknown_neighborhood_id = options.get("neighborhood_id")
        stats_only = options.get("stats_only", False)
        all_records = options.get("all_records", False)

        start_time = time.time()

        # Prepare the base query
        base_query = self._prepare_query(unknown_neighborhood_id, all_records)

        total_records = base_query.count()
        self.stdout.write(
            f"Found {total_records} biodiversity records with unknown neighborhood to process"
        )

        # Exit early if requested or if no records to process
        if stats_only:
            self.stdout.write("Stats-only mode, exiting without processing records")
            return

        if total_records == 0:
            self.stdout.write(self.style.WARNING("No records found to process."))
            return

        # Apply limit if specified
        if limit:
            self.stdout.write(f"Limiting to {limit} records")
            total_to_process = min(limit, total_records)
        else:
            total_to_process = total_records

        # Get filtered neighborhoods and localities
        filtered_neighborhoods, filtered_localities = self._get_filtered_boundaries(
            base_query, unknown_neighborhood_id
        )

        # Create a dictionary to cache "Desconocido en X" neighborhoods
        # Key: locality_id, Value: neighborhood
        unknown_neighborhood_cache = {}

        # Statistics tracking
        stats = {
            "updated_with_neighborhood": 0,
            "updated_with_locality": 0,
            "created_neighborhoods": 0,
            "non_matching_records": 0,
            "processed_records": 0,
        }

        # Get all record IDs before processing to prevent issues with pagination or filtering
        all_record_ids = list(base_query.values_list("id", flat=True))
        total_to_process = min(total_to_process, len(all_record_ids))

        # Process in batches for better performance
        with tqdm(total=total_to_process, desc="Processing records") as progress_bar:
            # Process IDs in batches
            for batch_start in range(0, total_to_process, batch_size):
                batch_end = min(batch_start + batch_size, total_to_process)
                batch_ids = all_record_ids[batch_start:batch_end]

                # Process the current batch
                processed_batch_size = self._process_batch(
                    batch_ids,
                    filtered_neighborhoods,
                    filtered_localities,
                    unknown_neighborhood_cache,
                    stats,
                    dry_run,
                )

                stats["processed_records"] += processed_batch_size
                progress_bar.update(processed_batch_size)

                # Print interim progress report
                if (
                    stats["processed_records"] % 1000 == 0
                    or batch_end == total_to_process
                ):
                    elapsed_time = time.time() - start_time
                    records_per_second = (
                        stats["processed_records"] / elapsed_time
                        if elapsed_time > 0
                        else 0
                    )
                    self.stdout.write(
                        f"Processed {stats['processed_records']}/{total_to_process} records "
                        f"({records_per_second:.2f} records/sec)"
                    )

        # Final report
        elapsed_time = time.time() - start_time
        self._print_final_report(stats, elapsed_time, dry_run)

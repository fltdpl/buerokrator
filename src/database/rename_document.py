from pathlib import Path

from src.organizer.category_mapper import (
    get_archive_category,
)
from src.organizer.filename_builder import (
    build_filename,
)
from src.processor.document_processor import (
    get_unique_target_path,
)


def rename_document(
    current_path,
    document_type,
    extracted_data,
):

    current_path = Path(current_path)

    category = get_archive_category(document_type)

    target_folder = Path("archive") / current_path.parent.parent.name / category

    target_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    classification = {
        "document_type": document_type,
    }

    new_filename = build_filename(
        classification,
        extracted_data,
        current_path.name,
    )

    target = target_folder / new_filename

    target = get_unique_target_path(target)

    current_path.rename(target)

    return target

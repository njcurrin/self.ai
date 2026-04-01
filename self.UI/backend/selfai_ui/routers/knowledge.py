from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Request
import logging

from selfai_ui.models.knowledge import (
    Knowledges,
    KnowledgeFiles,
    KnowledgeForm,
    KnowledgeResponse,
    KnowledgeUserResponse,
)
from selfai_ui.models.files import Files, FileModel
from selfai_ui.retrieval.vector.connector import VECTOR_DB_CLIENT
from selfai_ui.routers.retrieval import (
    process_file,
    ProcessFileForm,
    process_files_batch,
    BatchProcessFilesForm,
)


from selfai_ui.constants import ERROR_MESSAGES
from selfai_ui.utils.auth import get_verified_user
from selfai_ui.utils.access_control import has_access, has_permission
from selfai_ui.storage.provider import Storage
from selfai_ui.config import UPLOAD_DIR


from selfai_ui.env import SRC_LOG_LEVELS


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


def _move_file_to_kb(file: FileModel, knowledge_id: str) -> None:
    """Move a file into the KB's subdirectory. Rejects if file belongs to another KB."""
    import os

    if not file.path:
        return

    # Check if already in the correct KB subdirectory
    kb_dir = f"{UPLOAD_DIR}/{knowledge_id}/"
    if file.path.startswith(kb_dir) or f"/{knowledge_id}/" in file.path:
        return

    # Check if file is already in a different KB's subdirectory
    # Files in UPLOAD_DIR root (flat) are fine to move; files in another KB's dir are not
    parent = os.path.dirname(file.path)
    if parent != UPLOAD_DIR and os.path.basename(parent) != knowledge_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File already belongs to another knowledge base",
        )

    # Move the file
    try:
        new_path = Storage.move_file(file.path, knowledge_id)
        Files.update_file_path_by_id(file.id, new_path)
    except Exception as e:
        log.error(f"Failed to move file {file.id} to KB {knowledge_id}: {e}")


############################
# getKnowledgeBases
############################


@router.get("/", response_model=list[KnowledgeUserResponse])
async def get_knowledge(user=Depends(get_verified_user)):
    knowledge_bases = []

    if user.role == "admin":
        knowledge_bases = Knowledges.get_knowledge_bases()
    else:
        knowledge_bases = Knowledges.get_knowledge_bases_by_user_id(user.id, "read")

    # Get files for each knowledge base
    knowledge_with_files = []
    for knowledge_base in knowledge_bases:
        file_ids = KnowledgeFiles.get_file_ids_by_knowledge_id(knowledge_base.id)
        files = Files.get_file_metadatas_by_ids(file_ids) if file_ids else []

        knowledge_with_files.append(
            KnowledgeUserResponse(
                **knowledge_base.model_dump(),
                files=files,
            )
        )

    return knowledge_with_files


@router.get("/list", response_model=list[KnowledgeUserResponse])
async def get_knowledge_list(user=Depends(get_verified_user)):
    knowledge_bases = []

    if user.role == "admin":
        knowledge_bases = Knowledges.get_knowledge_bases()
    else:
        knowledge_bases = Knowledges.get_knowledge_bases_by_user_id(user.id, "write")

    # Get files for each knowledge base
    knowledge_with_files = []
    for knowledge_base in knowledge_bases:
        file_ids = KnowledgeFiles.get_file_ids_by_knowledge_id(knowledge_base.id)
        files = Files.get_file_metadatas_by_ids(file_ids) if file_ids else []

        knowledge_with_files.append(
            KnowledgeUserResponse(
                **knowledge_base.model_dump(),
                files=files,
            )
        )
    return knowledge_with_files


############################
# CreateNewKnowledge
############################


@router.post("/create", response_model=Optional[KnowledgeResponse])
async def create_new_knowledge(
    request: Request, form_data: KnowledgeForm, user=Depends(get_verified_user)
):
    if user.role != "admin" and not has_permission(
        user.id, "workspace.knowledge", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    knowledge = Knowledges.insert_new_knowledge(user.id, form_data)

    if knowledge:
        return knowledge
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.FILE_EXISTS,
        )


############################
# GetKnowledgeById
############################


class KnowledgeFilesResponse(KnowledgeResponse):
    files: list[FileModel]


@router.get("/{id}", response_model=Optional[KnowledgeFilesResponse])
async def get_knowledge_by_id(id: str, user=Depends(get_verified_user)):
    knowledge = Knowledges.get_knowledge_by_id(id=id)

    if knowledge:

        if (
            user.role == "admin"
            or knowledge.user_id == user.id
            or has_access(user.id, "read", knowledge.access_control)
        ):

            file_ids = KnowledgeFiles.get_file_ids_by_knowledge_id(id)
            files = Files.get_files_by_ids(file_ids)

            return KnowledgeFilesResponse(
                **knowledge.model_dump(),
                files=files,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateKnowledgeById
############################


@router.post("/{id}/update", response_model=Optional[KnowledgeFilesResponse])
async def update_knowledge_by_id(
    id: str,
    form_data: KnowledgeForm,
    user=Depends(get_verified_user),
):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if knowledge.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    knowledge = Knowledges.update_knowledge_by_id(id=id, form_data=form_data)
    if knowledge:
        file_ids = KnowledgeFiles.get_file_ids_by_knowledge_id(id)
        files = Files.get_files_by_ids(file_ids)

        return KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=files,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ID_TAKEN,
        )


############################
# AddFileToKnowledge
############################


class KnowledgeFileIdForm(BaseModel):
    file_id: str


@router.post("/{id}/file/add", response_model=Optional[KnowledgeFilesResponse])
def add_file_to_knowledge_by_id(
    request: Request,
    id: str,
    form_data: KnowledgeFileIdForm,
    user=Depends(get_verified_user),
):
    knowledge = Knowledges.get_knowledge_by_id(id=id)

    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if knowledge.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    file = Files.get_file_by_id(form_data.file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if not file.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.FILE_NOT_PROCESSED,
        )

    # Move file to KB subdirectory
    if file.path:
        _move_file_to_kb(file, id)

    # Add content to the vector database
    if not file.filename.endswith('_pipeline.json'):
        try:
            process_file(
                request, ProcessFileForm(file_id=form_data.file_id, collection_name=id)
            )
        except Exception as e:
            log.debug(e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    # Add file association via join table
    if not KnowledgeFiles.add_file_to_knowledge(id, form_data.file_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("knowledge"),
        )

    file_ids = KnowledgeFiles.get_file_ids_by_knowledge_id(id)
    files = Files.get_files_by_ids(file_ids)

    return KnowledgeFilesResponse(
        **knowledge.model_dump(),
        files=files,
    )


@router.post("/{id}/file/update", response_model=Optional[KnowledgeFilesResponse])
def update_file_from_knowledge_by_id(
    request: Request,
    id: str,
    form_data: KnowledgeFileIdForm,
    user=Depends(get_verified_user),
):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if knowledge.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    file = Files.get_file_by_id(form_data.file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Remove content from the vector database
    VECTOR_DB_CLIENT.delete(
        collection_name=knowledge.id, filter={"file_id": form_data.file_id}
    )

    # Add content to the vector database
    if not file.filename.endswith('_pipeline.json'):
        try:
            process_file(
                request, ProcessFileForm(file_id=form_data.file_id, collection_name=id)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    file_ids = KnowledgeFiles.get_file_ids_by_knowledge_id(id)
    files = Files.get_files_by_ids(file_ids)

    return KnowledgeFilesResponse(
        **knowledge.model_dump(),
        files=files,
    )


############################
# RemoveFileFromKnowledge
############################


@router.post("/{id}/file/remove", response_model=Optional[KnowledgeFilesResponse])
def remove_file_from_knowledge_by_id(
    id: str,
    form_data: KnowledgeFileIdForm,
    user=Depends(get_verified_user),
):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if knowledge.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    file = Files.get_file_by_id(form_data.file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Remove content from the vector database
    if not file.filename.endswith('_pipeline.json'):
        VECTOR_DB_CLIENT.delete(
            collection_name=knowledge.id, filter={"file_id": form_data.file_id}
        )

    # Remove file association via join table
    KnowledgeFiles.remove_file_from_knowledge(id, form_data.file_id)

    file_ids = KnowledgeFiles.get_file_ids_by_knowledge_id(id)
    files = Files.get_files_by_ids(file_ids)

    return KnowledgeFilesResponse(
        **knowledge.model_dump(),
        files=files,
    )


############################
# DeleteKnowledgeById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_knowledge_by_id(id: str, user=Depends(get_verified_user)):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if knowledge.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    try:
        VECTOR_DB_CLIENT.delete_collection(collection_name=id)
    except Exception as e:
        log.debug(e)
        pass
    Storage.delete_subdirectory(id)
    result = Knowledges.delete_knowledge_by_id(id=id)
    return result


############################
# ResetKnowledgeById
############################


@router.post("/{id}/reset", response_model=Optional[KnowledgeResponse])
async def reset_knowledge_by_id(id: str, user=Depends(get_verified_user)):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if knowledge.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    try:
        VECTOR_DB_CLIENT.delete_collection(collection_name=id)
    except Exception as e:
        log.debug(e)
        pass
    Storage.delete_subdirectory(id)
    KnowledgeFiles.remove_all_files_from_knowledge(id)

    knowledge = Knowledges.update_knowledge_data_by_id(id=id, data={"file_ids": []})

    return knowledge


############################
# AddFilesToKnowledge
############################


@router.post("/{id}/files/batch/add", response_model=Optional[KnowledgeFilesResponse])
def add_files_to_knowledge_batch(
    request: Request,
    id: str,
    form_data: list[KnowledgeFileIdForm],
    user=Depends(get_verified_user),
):
    """
    Add multiple files to a knowledge base
    """
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if knowledge.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Get files content and move to KB subdirectory
    print(f"files/batch/add - {len(form_data)} files")
    files: List[FileModel] = []
    for form in form_data:
        file = Files.get_file_by_id(form.file_id)
        if not file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {form.file_id} not found",
            )
        if file.path:
            _move_file_to_kb(file, id)
            file = Files.get_file_by_id(form.file_id)
        files.append(file)

    # Process files
    try:
        result = process_files_batch(
            request=request,
            form_data=BatchProcessFilesForm(files=files, collection_name=id),
            user=user,
        )
    except Exception as e:
        log.error(
            f"add_files_to_knowledge_batch: Exception occurred: {e}", exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Add successful files to knowledge base via join table
    successful_file_ids = [r.file_id for r in result.results if r.status == "completed"]
    for file_id in successful_file_ids:
        KnowledgeFiles.add_file_to_knowledge(id, file_id)

    all_file_ids = KnowledgeFiles.get_file_ids_by_knowledge_id(id)

    # Refresh knowledge for response
    knowledge = Knowledges.get_knowledge_by_id(id=id)

    # If there were any errors, include them in the response
    if result.errors:
        error_details = [f"{err.file_id}: {err.error}" for err in result.errors]
        return KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=Files.get_files_by_ids(all_file_ids),
            warnings={
                "message": "Some files failed to process",
                "errors": error_details,
            },
        )

    return KnowledgeFilesResponse(
        **knowledge.model_dump(), files=Files.get_files_by_ids(all_file_ids)
    )


############################
# PrepareInput (for Curator)
############################

@router.post("/{id}/prepare-input")
async def prepare_curator_input(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
):
    import json, os
    from datetime import datetime

    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.NOT_FOUND)

    # Iceberg path (future)
    if request.app.state.config.ICEBERG_BASE_URL:
        # TODO: return Iceberg table path for this KB
        raise HTTPException(status_code=501, detail="Iceberg not yet implemented")

    # JSONL export path — shared volume, curator-visible
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    curator_dir = os.path.join(UPLOAD_DIR, "curator")
    os.makedirs(curator_dir, exist_ok=True)
    output_file = os.path.join(curator_dir, f"{id}_{timestamp}.jsonl")

    # Pull extracted text from all non-pipeline files in this KB
    file_ids = KnowledgeFiles.get_file_ids_by_knowledge_id(id)
    files = Files.get_files_by_ids(file_ids)

    count = 0
    with open(output_file, "w") as f:
        for file in files:
            if (file.filename or "").endswith("_pipeline.json"):
                continue
            content = (file.data or {}).get("content", "")
            if not content:
                continue
            record = {
                "id": file.id,
                "text": content,
                "source": file.filename,
            }
            f.write(json.dumps(record) + "\n")
            count += 1

    log.info(f"Exported {count} files from KB {id} to {output_file}")

    # Return the curator-visible path (shared volume mount)
    curator_path = output_file.replace("/app/backend/data", "/workspace/ui-data")
    return {"input_path": curator_path, "file_count": count, "output_format": "parquet" if request.app.state.config.ICEBERG_BASE_URL else "jsonl"}

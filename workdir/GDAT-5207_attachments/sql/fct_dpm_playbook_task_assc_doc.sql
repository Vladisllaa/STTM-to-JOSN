SELECT
CAST(WORKSPACE_ID AS BIGINT) AS workspace_id,
CAST(PLAYBOOK_ID AS STRING) AS playbook_id,
CAST(TASK_ID AS STRING) AS task_id,
CAST(DOCUMENT_REVISION_ID AS BIGINT) AS document_revision_id,
CAST(DOCUMENT_FOLDER_ID AS BIGINT) AS document_folder_id,
CAST(DOCUMENT_ID AS BIGINT) AS document_id,
CAST(DOCUMENT_REFERENCE AS STRING) AS document_reference,
CAST(DOCUMENT_TITLE AS STRING) AS document_title,
CAST(IS_COMPLETE AS STRING) AS is_complete,
CAST(LOAD_DATE AS TIMESTAMP) AS load_date,
CAST(curdate() AS DATE) AS snapshot_date,
CAST(null AS STRING) AS contract_cd
FROM
dpm_playbook_task_assc_doc

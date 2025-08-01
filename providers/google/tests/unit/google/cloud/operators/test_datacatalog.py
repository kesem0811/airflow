# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from google.api_core.exceptions import AlreadyExists
from google.api_core.retry import Retry
from google.cloud.datacatalog import Entry, EntryGroup, Tag, TagTemplate, TagTemplateField
from google.protobuf.field_mask_pb2 import FieldMask

from airflow.exceptions import AirflowProviderDeprecationWarning
from airflow.providers.google.cloud.operators.datacatalog import (
    CloudDataCatalogCreateEntryGroupOperator,
    CloudDataCatalogCreateEntryOperator,
    CloudDataCatalogCreateTagOperator,
    CloudDataCatalogCreateTagTemplateFieldOperator,
    CloudDataCatalogCreateTagTemplateOperator,
    CloudDataCatalogDeleteEntryGroupOperator,
    CloudDataCatalogDeleteEntryOperator,
    CloudDataCatalogDeleteTagOperator,
    CloudDataCatalogDeleteTagTemplateFieldOperator,
    CloudDataCatalogDeleteTagTemplateOperator,
    CloudDataCatalogGetEntryGroupOperator,
    CloudDataCatalogGetEntryOperator,
    CloudDataCatalogGetTagTemplateOperator,
    CloudDataCatalogListTagsOperator,
    CloudDataCatalogLookupEntryOperator,
    CloudDataCatalogRenameTagTemplateFieldOperator,
    CloudDataCatalogSearchCatalogOperator,
    CloudDataCatalogUpdateEntryOperator,
    CloudDataCatalogUpdateTagOperator,
    CloudDataCatalogUpdateTagTemplateFieldOperator,
    CloudDataCatalogUpdateTagTemplateOperator,
)

from tests_common.test_utils.version_compat import AIRFLOW_V_3_0_PLUS

if TYPE_CHECKING:
    from google.api_core.gapic_v1.method import _MethodDefault

BASE_PATH = "airflow.providers.google.cloud.operators.datacatalog.{}"
TEST_PROJECT_ID: str = "example_id"
TEST_LOCATION: str = "en-west-3"
TEST_ENTRY_ID: str = "test-entry-id"
TEST_TAG_ID: str = "test-tag-id"
TEST_RETRY: Retry | _MethodDefault = Retry()
TEST_TIMEOUT: float = 0.5
TEST_METADATA: Sequence[tuple[str, str]] = []
TEST_GCP_CONN_ID: str = "test-gcp-conn-id"
TEST_IMPERSONATION_CHAIN: Sequence[str] = ["ACCOUNT_1", "ACCOUNT_2", "ACCOUNT_3"]
TEST_ENTRY_GROUP_ID: str = "test-entry-group-id"
TEST_TAG_TEMPLATE_ID: str = "test-tag-template-id"
TEST_TAG_TEMPLATE_FIELD_ID: str = "test-tag-template-field-id"
TEST_TAG_TEMPLATE_NAME: str = "test-tag-template-field-name"
TEST_FORCE: bool = False
TEST_READ_MASK: FieldMask = FieldMask(paths=["name"])
TEST_RESOURCE: str = "test-resource"
TEST_OPTIONS_: dict = {}
TEST_PAGE_SIZE: int = 50
TEST_LINKED_RESOURCE: str = "test-linked-resource"
TEST_SQL_RESOURCE: str = "test-sql-resource"
TEST_NEW_TAG_TEMPLATE_FIELD_ID: str = "test-new-tag-template-field-id"
TEST_SCOPE: dict = dict(include_project_ids=["example-scope-project"])
TEST_QUERY: str = "test-query"
TEST_ORDER_BY: str = "test-order-by"
TEST_UPDATE_MASK: dict = {"fields": ["name"]}
TEST_ENTRY_PATH: str = (
    f"projects/{TEST_PROJECT_ID}/locations/{TEST_LOCATION}"
    f"/entryGroups/{TEST_ENTRY_GROUP_ID}/entries/{TEST_ENTRY_ID}"
)
TEST_ENTRY_GROUP_PATH: str = (
    f"projects/{TEST_PROJECT_ID}/locations/{TEST_LOCATION}/entryGroups/{TEST_ENTRY_GROUP_ID}"
)
TEST_TAG_TEMPLATE_PATH: str = (
    f"projects/{TEST_PROJECT_ID}/locations/{TEST_LOCATION}/tagTemplates/{TEST_TAG_TEMPLATE_ID}"
)
TEST_TAG_PATH: str = (
    f"projects/{TEST_PROJECT_ID}/locations/{TEST_LOCATION}/entryGroups/"
    f"{TEST_ENTRY_GROUP_ID}/entries/{TEST_ENTRY_ID}/tags/{TEST_TAG_ID}"
)

TEST_ENTRY: Entry = Entry(name=TEST_ENTRY_PATH)
TEST_ENTRY_DICT: dict = {
    "description": "",
    "display_name": "",
    "linked_resource": "",
    "fully_qualified_name": "",
    "labels": {},
    "name": TEST_ENTRY_PATH,
}
TEST_ENTRY_GROUP: EntryGroup = EntryGroup(name=TEST_ENTRY_GROUP_PATH)
TEST_ENTRY_GROUP_DICT: dict = {
    "description": "",
    "display_name": "",
    "name": TEST_ENTRY_GROUP_PATH,
    "transferred_to_dataplex": False,
}
TEST_TAG: Tag = Tag(name=TEST_TAG_PATH)
TEST_TAG_DICT: dict = {
    "fields": {},
    "name": TEST_TAG_PATH,
    "template": "",
    "template_display_name": "",
    "dataplex_transfer_status": 0,
}
TEST_TAG_TEMPLATE: TagTemplate = TagTemplate(name=TEST_TAG_TEMPLATE_PATH)
TEST_TAG_TEMPLATE_DICT: dict = {
    "dataplex_transfer_status": 0,
    "display_name": "",
    "fields": {},
    "is_publicly_readable": False,
    "name": TEST_TAG_TEMPLATE_PATH,
}
TEST_TAG_TEMPLATE_FIELD: TagTemplateField = TagTemplateField(name=TEST_TAG_TEMPLATE_FIELD_ID)
TEST_TAG_TEMPLATE_FIELD_DICT: dict = {
    "description": "",
    "display_name": "",
    "is_required": False,
    "name": TEST_TAG_TEMPLATE_FIELD_ID,
    "order": 0,
}
TEST_ENTRY_LINK = "projects/{project_id}/locations/{location}/entryGroups/{entry_group_id}/entries/{entry_id}"
TEST_TAG_TEMPLATE_LINK = "projects/{project_id}/locations/{location}/tagTemplates/{tag_template_id}"
TEST_TAG_TEMPLATE_FIELD_LINK = "projects/{project_id}/locations/{location}/tagTemplates/{tag_template_id}\
    /fields/{tag_template_field_id}"


class TestCloudDataCatalogCreateEntryOperator:
    @mock.patch(
        "airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook",
        **{"return_value.create_entry.return_value": TEST_ENTRY},
    )
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogCreateEntryOperator(
                task_id="task_id",
                location=TEST_LOCATION,
                entry_group=TEST_ENTRY_GROUP_ID,
                entry_id=TEST_ENTRY_ID,
                entry=TEST_ENTRY,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        mock_ti = mock.MagicMock()
        mock_context = {"ti": mock_ti}
        if not AIRFLOW_V_3_0_PLUS:
            mock_context["task"] = task  # type: ignore[assignment]
        result = task.execute(context=mock_context)  # type: ignore[arg-type]
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.create_entry.assert_called_once_with(
            location=TEST_LOCATION,
            entry_group=TEST_ENTRY_GROUP_ID,
            entry_id=TEST_ENTRY_ID,
            entry=TEST_ENTRY,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )
        mock_ti.xcom_push.assert_any_call(
            key="entry_id",
            value=TEST_ENTRY_ID,
        )

        assert result == TEST_ENTRY_DICT

    @mock.patch("airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook")
    def test_assert_valid_hook_call_when_exists(self, mock_hook) -> None:
        mock_hook.return_value.create_entry.side_effect = AlreadyExists(message="message")
        mock_hook.return_value.get_entry.return_value = TEST_ENTRY
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogCreateEntryOperator(
                task_id="task_id",
                location=TEST_LOCATION,
                entry_group=TEST_ENTRY_GROUP_ID,
                entry_id=TEST_ENTRY_ID,
                entry=TEST_ENTRY,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        mock_ti = mock.MagicMock()
        mock_context = {"ti": mock_ti}
        if not AIRFLOW_V_3_0_PLUS:
            mock_context["task"] = task  # type: ignore[assignment]
        result = task.execute(context=mock_context)  # type: ignore[arg-type]
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.create_entry.assert_called_once_with(
            location=TEST_LOCATION,
            entry_group=TEST_ENTRY_GROUP_ID,
            entry_id=TEST_ENTRY_ID,
            entry=TEST_ENTRY,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )
        mock_hook.return_value.get_entry.assert_called_once_with(
            location=TEST_LOCATION,
            entry_group=TEST_ENTRY_GROUP_ID,
            entry=TEST_ENTRY_ID,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )
        mock_ti.xcom_push.assert_any_call(
            key="entry_id",
            value=TEST_ENTRY_ID,
        )
        assert result == TEST_ENTRY_DICT


class TestCloudDataCatalogCreateEntryGroupOperator:
    @mock.patch(
        "airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook",
        **{"return_value.create_entry_group.return_value": TEST_ENTRY_GROUP},
    )
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogCreateEntryGroupOperator(
                task_id="task_id",
                location=TEST_LOCATION,
                entry_group_id=TEST_ENTRY_GROUP_ID,
                entry_group=TEST_ENTRY_GROUP,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        mock_ti = mock.MagicMock()
        mock_context = {"ti": mock_ti}
        if not AIRFLOW_V_3_0_PLUS:
            mock_context["task"] = task  # type: ignore[assignment]
        result = task.execute(context=mock_context)  # type: ignore[arg-type]
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.create_entry_group.assert_called_once_with(
            location=TEST_LOCATION,
            entry_group_id=TEST_ENTRY_GROUP_ID,
            entry_group=TEST_ENTRY_GROUP,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )
        mock_ti.xcom_push.assert_any_call(
            key="entry_group_id",
            value=TEST_ENTRY_GROUP_ID,
        )
        assert result == TEST_ENTRY_GROUP_DICT


class TestCloudDataCatalogCreateTagOperator:
    @mock.patch(
        "airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook",
        **{"return_value.create_tag.return_value": TEST_TAG},
    )
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogCreateTagOperator(
                task_id="task_id",
                location=TEST_LOCATION,
                entry_group=TEST_ENTRY_GROUP_ID,
                entry=TEST_ENTRY_ID,
                tag=TEST_TAG,
                template_id=TEST_TAG_TEMPLATE_ID,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        mock_ti = mock.MagicMock()
        mock_context = {"ti": mock_ti}
        if not AIRFLOW_V_3_0_PLUS:
            mock_context["task"] = task  # type: ignore[assignment]
        result = task.execute(context=mock_context)  # type: ignore[arg-type]
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.create_tag.assert_called_once_with(
            location=TEST_LOCATION,
            entry_group=TEST_ENTRY_GROUP_ID,
            entry=TEST_ENTRY_ID,
            tag=TEST_TAG,
            template_id=TEST_TAG_TEMPLATE_ID,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )
        mock_ti.xcom_push.assert_any_call(
            key="tag_id",
            value=TEST_TAG_ID,
        )
        assert result == TEST_TAG_DICT


class TestCloudDataCatalogCreateTagTemplateOperator:
    @mock.patch(
        "airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook",
        **{"return_value.create_tag_template.return_value": TEST_TAG_TEMPLATE},
    )
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogCreateTagTemplateOperator(
                task_id="task_id",
                location=TEST_LOCATION,
                tag_template_id=TEST_TAG_TEMPLATE_ID,
                tag_template=TEST_TAG_TEMPLATE,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        mock_ti = mock.MagicMock()
        mock_context = {"ti": mock_ti}
        if not AIRFLOW_V_3_0_PLUS:
            mock_context["task"] = task  # type: ignore[assignment]
        result = task.execute(context=mock_context)  # type: ignore[arg-type]
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.create_tag_template.assert_called_once_with(
            location=TEST_LOCATION,
            tag_template_id=TEST_TAG_TEMPLATE_ID,
            tag_template=TEST_TAG_TEMPLATE,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )
        mock_ti.xcom_push.assert_any_call(
            key="tag_template_id",
            value=TEST_TAG_TEMPLATE_ID,
        )
        assert result == TEST_TAG_TEMPLATE_DICT


class TestCloudDataCatalogCreateTagTemplateFieldOperator:
    @mock.patch(
        "airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook",
        **{"return_value.create_tag_template_field.return_value": TEST_TAG_TEMPLATE_FIELD},
    )
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogCreateTagTemplateFieldOperator(
                task_id="task_id",
                location=TEST_LOCATION,
                tag_template=TEST_TAG_TEMPLATE_ID,
                tag_template_field_id=TEST_TAG_TEMPLATE_FIELD_ID,
                tag_template_field=TEST_TAG_TEMPLATE_FIELD,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        mock_ti = mock.MagicMock()
        mock_context = {"ti": mock_ti}
        if not AIRFLOW_V_3_0_PLUS:
            mock_context["task"] = task  # type: ignore[assignment]
        result = task.execute(context=mock_context)  # type: ignore[arg-type]
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.create_tag_template_field.assert_called_once_with(
            location=TEST_LOCATION,
            tag_template=TEST_TAG_TEMPLATE_ID,
            tag_template_field_id=TEST_TAG_TEMPLATE_FIELD_ID,
            tag_template_field=TEST_TAG_TEMPLATE_FIELD,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )
        mock_ti.xcom_push.assert_any_call(
            key="tag_template_field_id",
            value=TEST_TAG_TEMPLATE_FIELD_ID,
        )
        assert result == TEST_TAG_TEMPLATE_FIELD_DICT


class TestCloudDataCatalogDeleteEntryOperator:
    @mock.patch("airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook")
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogDeleteEntryOperator(
                task_id="task_id",
                location=TEST_LOCATION,
                entry_group=TEST_ENTRY_GROUP_ID,
                entry=TEST_ENTRY_ID,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        task.execute(context=mock.MagicMock())
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.delete_entry.assert_called_once_with(
            location=TEST_LOCATION,
            entry_group=TEST_ENTRY_GROUP_ID,
            entry=TEST_ENTRY_ID,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )


class TestCloudDataCatalogDeleteEntryGroupOperator:
    @mock.patch("airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook")
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogDeleteEntryGroupOperator(
                task_id="task_id",
                location=TEST_LOCATION,
                entry_group=TEST_ENTRY_GROUP_ID,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        task.execute(context=mock.MagicMock())
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.delete_entry_group.assert_called_once_with(
            location=TEST_LOCATION,
            entry_group=TEST_ENTRY_GROUP_ID,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )


class TestCloudDataCatalogDeleteTagOperator:
    @mock.patch("airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook")
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogDeleteTagOperator(
                task_id="task_id",
                location=TEST_LOCATION,
                entry_group=TEST_ENTRY_GROUP_ID,
                entry=TEST_ENTRY_ID,
                tag=TEST_TAG_ID,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        task.execute(context=mock.MagicMock())
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.delete_tag.assert_called_once_with(
            location=TEST_LOCATION,
            entry_group=TEST_ENTRY_GROUP_ID,
            entry=TEST_ENTRY_ID,
            tag=TEST_TAG_ID,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )


class TestCloudDataCatalogDeleteTagTemplateOperator:
    @mock.patch("airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook")
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogDeleteTagTemplateOperator(
                task_id="task_id",
                location=TEST_LOCATION,
                tag_template=TEST_TAG_TEMPLATE_ID,
                force=TEST_FORCE,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        task.execute(context=mock.MagicMock())
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.delete_tag_template.assert_called_once_with(
            location=TEST_LOCATION,
            tag_template=TEST_TAG_TEMPLATE_ID,
            force=TEST_FORCE,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )


class TestCloudDataCatalogDeleteTagTemplateFieldOperator:
    @mock.patch("airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook")
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogDeleteTagTemplateFieldOperator(
                task_id="task_id",
                location=TEST_LOCATION,
                tag_template=TEST_TAG_TEMPLATE_ID,
                field=TEST_TAG_TEMPLATE_FIELD_ID,
                force=TEST_FORCE,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        task.execute(context=mock.MagicMock())
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.delete_tag_template_field.assert_called_once_with(
            location=TEST_LOCATION,
            tag_template=TEST_TAG_TEMPLATE_ID,
            field=TEST_TAG_TEMPLATE_FIELD_ID,
            force=TEST_FORCE,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )


class TestCloudDataCatalogGetEntryOperator:
    @mock.patch(
        "airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook",
        **{"return_value.get_entry.return_value": TEST_ENTRY},
    )
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogGetEntryOperator(
                task_id="task_id",
                location=TEST_LOCATION,
                entry_group=TEST_ENTRY_GROUP_ID,
                entry=TEST_ENTRY_ID,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        task.execute(context=mock.MagicMock())
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.get_entry.assert_called_once_with(
            location=TEST_LOCATION,
            entry_group=TEST_ENTRY_GROUP_ID,
            entry=TEST_ENTRY_ID,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )


class TestCloudDataCatalogGetEntryGroupOperator:
    @mock.patch(
        "airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook",
        **{"return_value.get_entry_group.return_value": TEST_ENTRY_GROUP},
    )
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogGetEntryGroupOperator(
                task_id="task_id",
                location=TEST_LOCATION,
                entry_group=TEST_ENTRY_GROUP_ID,
                read_mask=TEST_READ_MASK,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        task.execute(context=mock.MagicMock())
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.get_entry_group.assert_called_once_with(
            location=TEST_LOCATION,
            entry_group=TEST_ENTRY_GROUP_ID,
            read_mask=TEST_READ_MASK,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )


class TestCloudDataCatalogGetTagTemplateOperator:
    @mock.patch(
        "airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook",
        **{"return_value.get_tag_template.return_value": TEST_TAG_TEMPLATE},
    )
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogGetTagTemplateOperator(
                task_id="task_id",
                location=TEST_LOCATION,
                tag_template=TEST_TAG_TEMPLATE_ID,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        task.execute(context=mock.MagicMock())
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.get_tag_template.assert_called_once_with(
            location=TEST_LOCATION,
            tag_template=TEST_TAG_TEMPLATE_ID,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )


class TestCloudDataCatalogListTagsOperator:
    @mock.patch(
        "airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook",
        return_value=mock.MagicMock(list_tags=mock.MagicMock(return_value=[TEST_TAG])),
    )
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogListTagsOperator(
                task_id="task_id",
                location=TEST_LOCATION,
                entry_group=TEST_ENTRY_GROUP_ID,
                entry=TEST_ENTRY_ID,
                page_size=TEST_PAGE_SIZE,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        task.execute(context=mock.MagicMock())
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.list_tags.assert_called_once_with(
            location=TEST_LOCATION,
            entry_group=TEST_ENTRY_GROUP_ID,
            entry=TEST_ENTRY_ID,
            page_size=TEST_PAGE_SIZE,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )


class TestCloudDataCatalogLookupEntryOperator:
    @mock.patch(
        "airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook",
        **{"return_value.lookup_entry.return_value": TEST_ENTRY},
    )
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogLookupEntryOperator(
                task_id="task_id",
                linked_resource=TEST_LINKED_RESOURCE,
                sql_resource=TEST_SQL_RESOURCE,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        task.execute(context=mock.MagicMock())
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.lookup_entry.assert_called_once_with(
            linked_resource=TEST_LINKED_RESOURCE,
            sql_resource=TEST_SQL_RESOURCE,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )


class TestCloudDataCatalogRenameTagTemplateFieldOperator:
    @mock.patch("airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook")
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogRenameTagTemplateFieldOperator(
                task_id="task_id",
                location=TEST_LOCATION,
                tag_template=TEST_TAG_TEMPLATE_ID,
                field=TEST_TAG_TEMPLATE_FIELD_ID,
                new_tag_template_field_id=TEST_NEW_TAG_TEMPLATE_FIELD_ID,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        task.execute(context=mock.MagicMock())
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.rename_tag_template_field.assert_called_once_with(
            location=TEST_LOCATION,
            tag_template=TEST_TAG_TEMPLATE_ID,
            field=TEST_TAG_TEMPLATE_FIELD_ID,
            new_tag_template_field_id=TEST_NEW_TAG_TEMPLATE_FIELD_ID,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )


class TestCloudDataCatalogSearchCatalogOperator:
    @mock.patch("airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook")
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogSearchCatalogOperator(
                task_id="task_id",
                scope=TEST_SCOPE,
                query=TEST_QUERY,
                page_size=TEST_PAGE_SIZE,
                order_by=TEST_ORDER_BY,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        task.execute(context=mock.MagicMock())
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.search_catalog.assert_called_once_with(
            scope=TEST_SCOPE,
            query=TEST_QUERY,
            page_size=TEST_PAGE_SIZE,
            order_by=TEST_ORDER_BY,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )


class TestCloudDataCatalogUpdateEntryOperator:
    @mock.patch("airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook")
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        mock_hook.return_value.update_entry.return_value.name = TEST_ENTRY_LINK.format(
            project_id=TEST_PROJECT_ID,
            location=TEST_LOCATION,
            entry_group_id=TEST_ENTRY_GROUP_ID,
            entry_id=TEST_ENTRY_ID,
        )
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogUpdateEntryOperator(
                task_id="task_id",
                entry=TEST_ENTRY,
                update_mask=TEST_UPDATE_MASK,
                location=TEST_LOCATION,
                entry_group=TEST_ENTRY_GROUP_ID,
                entry_id=TEST_ENTRY_ID,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        task.execute(context=mock.MagicMock())
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.update_entry.assert_called_once_with(
            entry=TEST_ENTRY,
            update_mask=TEST_UPDATE_MASK,
            location=TEST_LOCATION,
            entry_group=TEST_ENTRY_GROUP_ID,
            entry_id=TEST_ENTRY_ID,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )


class TestCloudDataCatalogUpdateTagOperator:
    @mock.patch("airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook")
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        mock_hook.return_value.update_tag.return_value.name = TEST_ENTRY_LINK.format(
            project_id=TEST_PROJECT_ID,
            location=TEST_LOCATION,
            entry_group_id=TEST_ENTRY_GROUP_ID,
            entry_id=TEST_ENTRY_ID,
        )
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogUpdateTagOperator(
                task_id="task_id",
                tag=Tag(name=TEST_TAG_ID),
                update_mask=TEST_UPDATE_MASK,
                location=TEST_LOCATION,
                entry_group=TEST_ENTRY_GROUP_ID,
                entry=TEST_ENTRY_ID,
                tag_id=TEST_TAG_ID,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        task.execute(context=mock.MagicMock())
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.update_tag.assert_called_once_with(
            tag=Tag(name=TEST_TAG_ID),
            update_mask=TEST_UPDATE_MASK,
            location=TEST_LOCATION,
            entry_group=TEST_ENTRY_GROUP_ID,
            entry=TEST_ENTRY_ID,
            tag_id=TEST_TAG_ID,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )


class TestCloudDataCatalogUpdateTagTemplateOperator:
    @mock.patch("airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook")
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        mock_hook.return_value.update_tag_template.return_value.name = TEST_TAG_TEMPLATE_LINK.format(
            project_id=TEST_PROJECT_ID,
            location=TEST_LOCATION,
            tag_template_id=TEST_TAG_TEMPLATE_ID,
        )
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogUpdateTagTemplateOperator(
                task_id="task_id",
                tag_template=TagTemplate(name=TEST_TAG_TEMPLATE_ID),
                update_mask=TEST_UPDATE_MASK,
                location=TEST_LOCATION,
                tag_template_id=TEST_TAG_TEMPLATE_ID,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        task.execute(context=mock.MagicMock())
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.update_tag_template.assert_called_once_with(
            tag_template=TagTemplate(name=TEST_TAG_TEMPLATE_ID),
            update_mask=TEST_UPDATE_MASK,
            location=TEST_LOCATION,
            tag_template_id=TEST_TAG_TEMPLATE_ID,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )


class TestCloudDataCatalogUpdateTagTemplateFieldOperator:
    @mock.patch("airflow.providers.google.cloud.operators.datacatalog.CloudDataCatalogHook")
    def test_assert_valid_hook_call(self, mock_hook) -> None:
        mock_hook.return_value.update_tag_template_field.return_value.name = (
            TEST_TAG_TEMPLATE_FIELD_LINK.format(
                project_id=TEST_PROJECT_ID,
                location=TEST_LOCATION,
                tag_template_id=TEST_TAG_TEMPLATE_ID,
                tag_template_field_id=TEST_TAG_TEMPLATE_FIELD_ID,
            )
        )
        with pytest.warns(AirflowProviderDeprecationWarning):
            task = CloudDataCatalogUpdateTagTemplateFieldOperator(
                task_id="task_id",
                tag_template_field=TEST_TAG_TEMPLATE_FIELD,
                update_mask=TEST_UPDATE_MASK,
                tag_template_field_name=TEST_TAG_TEMPLATE_NAME,
                location=TEST_LOCATION,
                tag_template=TEST_TAG_TEMPLATE_ID,
                tag_template_field_id=TEST_TAG_TEMPLATE_FIELD_ID,
                project_id=TEST_PROJECT_ID,
                retry=TEST_RETRY,
                timeout=TEST_TIMEOUT,
                metadata=TEST_METADATA,
                gcp_conn_id=TEST_GCP_CONN_ID,
                impersonation_chain=TEST_IMPERSONATION_CHAIN,
            )
        task.execute(context=mock.MagicMock())
        mock_hook.assert_called_once_with(
            gcp_conn_id=TEST_GCP_CONN_ID,
            impersonation_chain=TEST_IMPERSONATION_CHAIN,
        )
        mock_hook.return_value.update_tag_template_field.assert_called_once_with(
            tag_template_field=TEST_TAG_TEMPLATE_FIELD,
            update_mask=TEST_UPDATE_MASK,
            tag_template_field_name=TEST_TAG_TEMPLATE_NAME,
            location=TEST_LOCATION,
            tag_template=TEST_TAG_TEMPLATE_ID,
            tag_template_field_id=TEST_TAG_TEMPLATE_FIELD_ID,
            project_id=TEST_PROJECT_ID,
            retry=TEST_RETRY,
            timeout=TEST_TIMEOUT,
            metadata=TEST_METADATA,
        )

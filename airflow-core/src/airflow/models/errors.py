#
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

from sqlalchemy import Column, Integer, String, Text

from airflow.dag_processing.bundles.manager import DagBundlesManager
from airflow.models.base import Base, StringID
from airflow.utils.sqlalchemy import UtcDateTime


class ParseImportError(Base):
    """Stores all Import Errors which are recorded when parsing DAGs and displayed on the Webserver."""

    __tablename__ = "import_error"
    id = Column(Integer, primary_key=True)
    timestamp = Column(UtcDateTime)
    filename = Column(String(1024))
    bundle_name = Column(StringID())
    stacktrace = Column(Text)

    def full_file_path(self) -> str:
        """Return the full file path of the dag."""
        bundle = DagBundlesManager().get_bundle(self.bundle_name)
        return "/".join([str(bundle.path), self.filename])

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

import base64
import os
from io import StringIO
from pathlib import Path
from unittest.mock import call, mock_open, patch

import pytest

from airflow.exceptions import AirflowException
from airflow.models import Connection
from airflow.providers.apache.spark.hooks.spark_submit import SparkSubmitHook

pytestmark = pytest.mark.db_test


class TestSparkSubmitHook:
    _spark_job_file = "test_application.py"
    _config = {
        "conf": {"parquet.compression": "SNAPPY"},
        "conn_id": "default_spark",
        "files": "hive-site.xml",
        "py_files": "sample_library.py",
        "archives": "sample_archive.zip#SAMPLE",
        "jars": "parquet.jar",
        "packages": "com.databricks:spark-avro_2.11:3.2.0",
        "exclude_packages": "org.bad.dependency:1.0.0",
        "repositories": "http://myrepo.org",
        "total_executor_cores": 4,
        "executor_cores": 4,
        "executor_memory": "22g",
        "keytab": "privileged_user.keytab",
        "principal": "user/spark@airflow.org",
        "proxy_user": "sample_user",
        "name": "spark-job",
        "num_executors": 10,
        "verbose": True,
        "driver_memory": "3g",
        "java_class": "com.foo.bar.AppMain",
        "application_args": [
            "-f",
            "foo",
            "--bar",
            "bar",
            "--with-spaces",
            "args should keep embedded spaces",
            "baz",
        ],
        "use_krb5ccache": True,
    }

    @staticmethod
    def cmd_args_to_dict(list_cmd):
        return_dict = {}
        for arg1, arg2 in zip(list_cmd, list_cmd[1:]):
            if arg1.startswith("--"):
                return_dict[arg1] = arg2
        return return_dict

    @pytest.fixture(autouse=True)
    def setup_connections(self, create_connection_without_db):
        create_connection_without_db(
            Connection(
                conn_id="spark_yarn_cluster",
                conn_type="spark",
                host="yarn://yarn-master",
                extra='{"queue": "root.etl", "deploy-mode": "cluster"}',
            )
        )
        create_connection_without_db(
            Connection(
                conn_id="spark_k8s_cluster",
                conn_type="spark",
                host="k8s://https://k8s-master",
                extra='{"deploy-mode": "cluster", "namespace": "mynamespace"}',
            )
        )
        create_connection_without_db(
            Connection(
                conn_id="spark_k8s_client",
                conn_type="spark",
                host="k8s://https://k8s-master",
                extra='{"deploy-mode": "client", "namespace": "mynamespace"}',
            )
        )
        create_connection_without_db(
            Connection(conn_id="spark_default_mesos", conn_type="spark", host="mesos://host", port=5050)
        )

        create_connection_without_db(
            Connection(
                conn_id="spark_binary_set",
                conn_type="spark",
                host="yarn",
                extra='{"spark-binary": "spark2-submit"}',
            )
        )
        create_connection_without_db(
            Connection(
                conn_id="spark_binary_set_spark3_submit",
                conn_type="spark",
                host="yarn",
                extra='{"spark-binary": "spark3-submit"}',
            )
        )
        create_connection_without_db(
            Connection(
                conn_id="spark_custom_binary_set",
                conn_type="spark",
                host="yarn",
                extra='{"spark-binary": "spark-other-submit"}',
            )
        )
        create_connection_without_db(
            Connection(
                conn_id="spark_home_set",
                conn_type="spark",
                host="yarn",
                extra='{"spark-home": "/custom/spark-home/path"}',
            )
        )
        create_connection_without_db(
            Connection(
                conn_id="spark_standalone_cluster",
                conn_type="spark",
                host="spark://spark-standalone-master:6066",
                extra='{"deploy-mode": "cluster"}',
            )
        )
        create_connection_without_db(
            Connection(
                conn_id="spark_standalone_cluster_client_mode",
                conn_type="spark",
                host="spark://spark-standalone-master:6066",
                extra='{"deploy-mode": "client"}',
            )
        )
        create_connection_without_db(
            Connection(
                conn_id="spark_principal_set",
                conn_type="spark",
                host="yarn",
                extra='{"principal": "user/spark@airflow.org"}',
            )
        )
        create_connection_without_db(
            Connection(
                conn_id="spark_keytab_set",
                conn_type="spark",
                host="yarn",
                extra='{"keytab": "privileged_user.keytab"}',
            )
        )

    @patch(
        "airflow.providers.apache.spark.hooks.spark_submit.os.getenv", return_value="/tmp/airflow_krb5_ccache"
    )
    def test_build_spark_submit_command(self, mock_get_env):
        # Given
        hook = SparkSubmitHook(**self._config)

        # When
        cmd = hook._build_spark_submit_command(self._spark_job_file)

        # Then
        expected_build_cmd = [
            "spark-submit",
            "--master",
            "yarn",
            "--conf",
            "parquet.compression=SNAPPY",
            "--files",
            "hive-site.xml",
            "--py-files",
            "sample_library.py",
            "--archives",
            "sample_archive.zip#SAMPLE",
            "--jars",
            "parquet.jar",
            "--packages",
            "com.databricks:spark-avro_2.11:3.2.0",
            "--exclude-packages",
            "org.bad.dependency:1.0.0",
            "--repositories",
            "http://myrepo.org",
            "--num-executors",
            "10",
            "--total-executor-cores",
            "4",
            "--executor-cores",
            "4",
            "--executor-memory",
            "22g",
            "--driver-memory",
            "3g",
            "--keytab",
            "privileged_user.keytab",
            "--principal",
            "user/spark@airflow.org",
            "--conf",
            "spark.kerberos.renewal.credentials=ccache",
            "--proxy-user",
            "sample_user",
            "--name",
            "spark-job",
            "--class",
            "com.foo.bar.AppMain",
            "--verbose",
            "test_application.py",
            "-f",
            "foo",
            "--bar",
            "bar",
            "--with-spaces",
            "args should keep embedded spaces",
            "baz",
        ]
        assert expected_build_cmd == cmd
        mock_get_env.assert_called_with("KRB5CCNAME")

    @patch("airflow.configuration.conf.get_mandatory_value")
    def test_resolve_spark_submit_env_vars_use_krb5ccache_missing_principal(self, mock_get_madantory_value):
        mock_principal = "airflow"
        mock_get_madantory_value.return_value = mock_principal
        hook = SparkSubmitHook(conn_id="spark_yarn_cluster", principal=None, use_krb5ccache=True)
        mock_get_madantory_value.assert_called_with("kerberos", "principal")
        assert hook._principal == mock_principal

    def test_resolve_spark_submit_env_vars_use_krb5ccache_missing_KRB5CCNAME_env(self):
        hook = SparkSubmitHook(
            conn_id="spark_yarn_cluster", principal="user/spark@airflow.org", use_krb5ccache=True
        )
        with pytest.raises(
            AirflowException,
            match="KRB5CCNAME environment variable required to use ticket ccache is missing.",
        ):
            hook._build_spark_submit_command(self._spark_job_file)

    def test_build_track_driver_status_command(self):
        # note this function is only relevant for spark setup matching below condition
        # 'spark://' in self._connection['master'] and self._connection['deploy_mode'] == 'cluster'

        # Given
        hook_spark_standalone_cluster = SparkSubmitHook(conn_id="spark_standalone_cluster")
        hook_spark_standalone_cluster._driver_id = "driver-20171128111416-0001"
        hook_spark_yarn_cluster = SparkSubmitHook(conn_id="spark_yarn_cluster")
        hook_spark_yarn_cluster._driver_id = "driver-20171128111417-0001"

        # When
        build_track_driver_status_spark_standalone_cluster = (
            hook_spark_standalone_cluster._build_track_driver_status_command()
        )
        build_track_driver_status_spark_yarn_cluster = (
            hook_spark_yarn_cluster._build_track_driver_status_command()
        )

        # Then
        expected_spark_standalone_cluster = [
            "/usr/bin/curl",
            "--max-time",
            "30",
            "http://spark-standalone-master:6066/v1/submissions/status/driver-20171128111416-0001",
        ]
        expected_spark_yarn_cluster = [
            "spark-submit",
            "--master",
            "yarn://yarn-master",
            "--status",
            "driver-20171128111417-0001",
        ]

        assert expected_spark_standalone_cluster == build_track_driver_status_spark_standalone_cluster
        assert expected_spark_yarn_cluster == build_track_driver_status_spark_yarn_cluster

    @patch("airflow.providers.apache.spark.hooks.spark_submit.subprocess.Popen")
    def test_spark_process_runcmd(self, mock_popen):
        # Given
        mock_popen.return_value.stdout = StringIO("stdout")
        mock_popen.return_value.stderr = StringIO("stderr")
        mock_popen.return_value.wait.return_value = 0

        # When
        hook = SparkSubmitHook(conn_id="")
        hook.submit()

        # Then
        assert mock_popen.mock_calls[0] == call(
            ["spark-submit", "--master", "yarn", "--name", "default-name", ""],
            stderr=-2,
            stdout=-1,
            universal_newlines=True,
            bufsize=-1,
        )

    def test_resolve_should_track_driver_status(self):
        # Given
        hook_default = SparkSubmitHook(conn_id="")
        hook_spark_yarn_cluster = SparkSubmitHook(conn_id="spark_yarn_cluster")
        hook_spark_k8s_cluster = SparkSubmitHook(conn_id="spark_k8s_cluster")
        hook_spark_default_mesos = SparkSubmitHook(conn_id="spark_default_mesos")
        hook_spark_binary_set = SparkSubmitHook(conn_id="spark_binary_set")
        hook_spark_standalone_cluster = SparkSubmitHook(conn_id="spark_standalone_cluster")

        # When
        should_track_driver_status_default = hook_default._resolve_should_track_driver_status()
        should_track_driver_status_spark_yarn_cluster = (
            hook_spark_yarn_cluster._resolve_should_track_driver_status()
        )
        should_track_driver_status_spark_k8s_cluster = (
            hook_spark_k8s_cluster._resolve_should_track_driver_status()
        )
        should_track_driver_status_spark_default_mesos = (
            hook_spark_default_mesos._resolve_should_track_driver_status()
        )
        should_track_driver_status_spark_binary_set = (
            hook_spark_binary_set._resolve_should_track_driver_status()
        )
        should_track_driver_status_spark_standalone_cluster = (
            hook_spark_standalone_cluster._resolve_should_track_driver_status()
        )

        # Then
        assert should_track_driver_status_default is False
        assert should_track_driver_status_spark_yarn_cluster is False
        assert should_track_driver_status_spark_k8s_cluster is False
        assert should_track_driver_status_spark_default_mesos is False
        assert should_track_driver_status_spark_binary_set is False
        assert should_track_driver_status_spark_standalone_cluster is True

    def test_resolve_connection_yarn_default(self):
        # Given
        hook = SparkSubmitHook(conn_id="")

        # When
        connection = hook._resolve_connection()
        cmd = hook._build_spark_submit_command(self._spark_job_file)

        # Then
        dict_cmd = self.cmd_args_to_dict(cmd)
        expected_spark_connection = {
            "master": "yarn",
            "spark_binary": "spark-submit",
            "deploy_mode": None,
            "queue": None,
            "namespace": None,
            "principal": None,
            "keytab": None,
        }
        assert connection == expected_spark_connection
        assert dict_cmd["--master"] == "yarn"

    def test_resolve_connection_yarn_default_connection(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_default")

        # When
        connection = hook._resolve_connection()
        cmd = hook._build_spark_submit_command(self._spark_job_file)

        # Then
        dict_cmd = self.cmd_args_to_dict(cmd)
        expected_spark_connection = {
            "master": "yarn",
            "spark_binary": "spark-submit",
            "deploy_mode": None,
            "queue": "root.default",
            "namespace": None,
            "principal": None,
            "keytab": None,
        }
        assert connection == expected_spark_connection
        assert dict_cmd["--master"] == "yarn"
        assert dict_cmd["--queue"] == "root.default"

    def test_resolve_connection_mesos_default_connection(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_default_mesos")

        # When
        connection = hook._resolve_connection()
        cmd = hook._build_spark_submit_command(self._spark_job_file)

        # Then
        dict_cmd = self.cmd_args_to_dict(cmd)
        expected_spark_connection = {
            "master": "mesos://host:5050",
            "spark_binary": "spark-submit",
            "deploy_mode": None,
            "queue": None,
            "namespace": None,
            "principal": None,
            "keytab": None,
        }
        assert connection == expected_spark_connection
        assert dict_cmd["--master"] == "mesos://host:5050"

    def test_resolve_connection_spark_yarn_cluster_connection(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_yarn_cluster")

        # When
        connection = hook._resolve_connection()
        cmd = hook._build_spark_submit_command(self._spark_job_file)

        # Then
        dict_cmd = self.cmd_args_to_dict(cmd)
        expected_spark_connection = {
            "master": "yarn://yarn-master",
            "spark_binary": "spark-submit",
            "deploy_mode": "cluster",
            "queue": "root.etl",
            "namespace": None,
            "principal": None,
            "keytab": None,
        }
        assert connection == expected_spark_connection
        assert dict_cmd["--master"] == "yarn://yarn-master"
        assert dict_cmd["--queue"] == "root.etl"
        assert dict_cmd["--deploy-mode"] == "cluster"

    def test_resolve_connection_spark_k8s_cluster_connection(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_k8s_cluster")

        # When
        connection = hook._resolve_connection()
        cmd = hook._build_spark_submit_command(self._spark_job_file)

        # Then
        dict_cmd = self.cmd_args_to_dict(cmd)
        expected_spark_connection = {
            "queue": None,
            "spark_binary": "spark-submit",
            "master": "k8s://https://k8s-master",
            "deploy_mode": "cluster",
            "namespace": "mynamespace",
            "principal": None,
            "keytab": None,
        }
        assert connection == expected_spark_connection
        assert dict_cmd["--master"] == "k8s://https://k8s-master"
        assert dict_cmd["--deploy-mode"] == "cluster"

    def test_resolve_connection_spark_k8s_cluster_ns_conf(self):
        # Given we specify the config option directly
        conf = {
            "spark.kubernetes.namespace": "airflow",
        }
        hook = SparkSubmitHook(conn_id="spark_k8s_cluster", conf=conf)

        # When
        connection = hook._resolve_connection()
        cmd = hook._build_spark_submit_command(self._spark_job_file)

        # Then
        dict_cmd = self.cmd_args_to_dict(cmd)
        expected_spark_connection = {
            "queue": None,
            "spark_binary": "spark-submit",
            "master": "k8s://https://k8s-master",
            "deploy_mode": "cluster",
            "namespace": "airflow",
            "principal": None,
            "keytab": None,
        }
        assert connection == expected_spark_connection
        assert dict_cmd["--master"] == "k8s://https://k8s-master"
        assert dict_cmd["--deploy-mode"] == "cluster"
        assert dict_cmd["--conf"] == "spark.kubernetes.namespace=airflow"

    def test_resolve_connection_spark_binary_set_connection(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_binary_set")

        # When
        connection = hook._resolve_connection()
        cmd = hook._build_spark_submit_command(self._spark_job_file)

        # Then
        expected_spark_connection = {
            "master": "yarn",
            "spark_binary": "spark2-submit",
            "deploy_mode": None,
            "queue": None,
            "namespace": None,
            "principal": None,
            "keytab": None,
        }
        assert connection == expected_spark_connection
        assert cmd[0] == "spark2-submit"

    def test_resolve_connection_spark_binary_spark3_submit_set_connection(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_binary_set_spark3_submit")

        # When
        connection = hook._resolve_connection()
        cmd = hook._build_spark_submit_command(self._spark_job_file)

        # Then
        expected_spark_connection = {
            "master": "yarn",
            "spark_binary": "spark3-submit",
            "deploy_mode": None,
            "queue": None,
            "namespace": None,
            "principal": None,
            "keytab": None,
        }
        assert connection == expected_spark_connection
        assert cmd[0] == "spark3-submit"

    def test_resolve_connection_custom_spark_binary_allowed_in_hook(self):
        SparkSubmitHook(conn_id="spark_binary_set", spark_binary="another-custom-spark-submit")

    def test_resolve_connection_spark_binary_extra_not_allowed_runtime_error(self):
        with pytest.raises(RuntimeError):
            SparkSubmitHook(conn_id="spark_custom_binary_set")

    def test_resolve_connection_spark_home_not_allowed_runtime_error(self):
        with pytest.raises(RuntimeError):
            SparkSubmitHook(conn_id="spark_home_set")

    def test_resolve_connection_spark_binary_default_value_override(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_binary_set", spark_binary="spark3-submit")

        # When
        connection = hook._resolve_connection()
        cmd = hook._build_spark_submit_command(self._spark_job_file)

        # Then
        expected_spark_connection = {
            "master": "yarn",
            "spark_binary": "spark3-submit",
            "deploy_mode": None,
            "queue": None,
            "namespace": None,
            "principal": None,
            "keytab": None,
        }
        assert connection == expected_spark_connection
        assert cmd[0] == "spark3-submit"

    def test_resolve_connection_spark_binary_default_value(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_default")

        # When
        connection = hook._resolve_connection()
        cmd = hook._build_spark_submit_command(self._spark_job_file)

        # Then
        expected_spark_connection = {
            "master": "yarn",
            "spark_binary": "spark-submit",
            "deploy_mode": None,
            "queue": "root.default",
            "namespace": None,
            "principal": None,
            "keytab": None,
        }
        assert connection == expected_spark_connection
        assert cmd[0] == "spark-submit"

    def test_resolve_connection_spark_standalone_cluster_connection(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_standalone_cluster")

        # When
        connection = hook._resolve_connection()
        cmd = hook._build_spark_submit_command(self._spark_job_file)

        # Then
        expected_spark_connection = {
            "master": "spark://spark-standalone-master:6066",
            "spark_binary": "spark-submit",
            "deploy_mode": "cluster",
            "queue": None,
            "namespace": None,
            "principal": None,
            "keytab": None,
        }
        assert connection == expected_spark_connection
        assert cmd[0] == "spark-submit"

    def test_resolve_connection_principal_set_connection(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_principal_set")

        # When
        connection = hook._resolve_connection()
        cmd = hook._build_spark_submit_command(self._spark_job_file)

        # Then
        dict_cmd = self.cmd_args_to_dict(cmd)
        expected_spark_connection = {
            "master": "yarn",
            "spark_binary": "spark-submit",
            "deploy_mode": None,
            "queue": None,
            "namespace": None,
            "principal": "user/spark@airflow.org",
            "keytab": None,
        }
        assert connection == expected_spark_connection
        assert dict_cmd["--principal"] == "user/spark@airflow.org"

    def test_resolve_connection_principal_value_override(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_principal_set", principal="will-override")

        # When
        connection = hook._resolve_connection()
        cmd = hook._build_spark_submit_command(self._spark_job_file)

        # Then
        dict_cmd = self.cmd_args_to_dict(cmd)
        expected_spark_connection = {
            "master": "yarn",
            "spark_binary": "spark-submit",
            "deploy_mode": None,
            "queue": None,
            "namespace": None,
            "principal": "will-override",
            "keytab": None,
        }
        assert connection == expected_spark_connection
        assert dict_cmd["--principal"] == "will-override"

    @patch(
        "airflow.providers.apache.spark.hooks.spark_submit.SparkSubmitHook._create_keytab_path_from_base64_keytab",
        return_value="privileged_user.keytab",
    )
    def test_resolve_connection_keytab_set_connection(self, mock_create_keytab_path_from_base64_keytab):
        # Given
        hook = SparkSubmitHook(conn_id="spark_keytab_set")

        # When
        connection = hook._resolve_connection()
        cmd = hook._build_spark_submit_command(self._spark_job_file)

        # Then
        dict_cmd = self.cmd_args_to_dict(cmd)
        expected_spark_connection = {
            "master": "yarn",
            "spark_binary": "spark-submit",
            "deploy_mode": None,
            "queue": None,
            "namespace": None,
            "principal": None,
            "keytab": "privileged_user.keytab",
        }
        assert connection == expected_spark_connection
        assert dict_cmd["--keytab"] == "privileged_user.keytab"

    @patch(
        "airflow.providers.apache.spark.hooks.spark_submit.SparkSubmitHook._create_keytab_path_from_base64_keytab"
    )
    def test_resolve_connection_keytab_value_override(self, mock_create_keytab_path_from_base64_keytab):
        # Given
        hook = SparkSubmitHook(conn_id="spark_keytab_set", keytab="will-override")

        # When
        connection = hook._resolve_connection()
        cmd = hook._build_spark_submit_command(self._spark_job_file)

        # Then
        dict_cmd = self.cmd_args_to_dict(cmd)
        expected_spark_connection = {
            "master": "yarn",
            "spark_binary": "spark-submit",
            "deploy_mode": None,
            "queue": None,
            "namespace": None,
            "principal": None,
            "keytab": "will-override",
        }
        assert connection == expected_spark_connection
        assert dict_cmd["--keytab"] == "will-override"
        assert not mock_create_keytab_path_from_base64_keytab.called, (
            "Should not call _create_keytab_path_from_base64_keytab"
        )

    def test_resolve_spark_submit_env_vars_standalone_client_mode(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_standalone_cluster_client_mode", env_vars={"bar": "foo"})

        # When
        hook._build_spark_submit_command(self._spark_job_file)

        # Then
        assert hook._env == {"bar": "foo"}

    def test_resolve_spark_submit_env_vars_standalone_cluster_mode(self):
        def env_vars_exception_in_standalone_cluster_mode():
            # Given
            hook = SparkSubmitHook(conn_id="spark_standalone_cluster", env_vars={"bar": "foo"})

            # When
            hook._build_spark_submit_command(self._spark_job_file)

        # Then
        with pytest.raises(AirflowException):
            env_vars_exception_in_standalone_cluster_mode()

    def test_resolve_spark_submit_env_vars_yarn(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_yarn_cluster", env_vars={"bar": "foo"})

        # When
        cmd = hook._build_spark_submit_command(self._spark_job_file)

        # Then
        assert cmd[4] == "spark.yarn.appMasterEnv.bar=foo"
        assert hook._env == {"bar": "foo"}

    def test_resolve_spark_submit_env_vars_k8s(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_k8s_cluster", env_vars={"bar": "foo"})

        # When
        cmd = hook._build_spark_submit_command(self._spark_job_file)

        # Then
        assert cmd[4] == "spark.kubernetes.driverEnv.bar=foo"

    def test_process_spark_submit_log_yarn(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_yarn_cluster")
        log_lines = [
            "SPARK_MAJOR_VERSION is set to 2, using Spark2",
            "WARN NativeCodeLoader: Unable to load native-hadoop library for your "
            "platform... using builtin-java classes where applicable",
            "WARN DomainSocketFactory: The short-circuit local reads feature cannot "
            "be used because libhadoop cannot be loaded.",
            "INFO Client: Requesting a new application from cluster with 10 NodeManagers",
            "INFO Client: Submitting application application_1486558679801_1820 to ResourceManager",
        ]
        # When
        hook._process_spark_submit_log(log_lines)

        # Then

        assert hook._yarn_application_id == "application_1486558679801_1820"

    @pytest.mark.parametrize(
        "pod_name",
        [
            "spark-pi-edf2ace37be7353a958b38733a12f8e6-driver",
            "spark-pi-driver-edf2ace37be7353a958b38733a12f8e6-driver",
        ],
    )
    def test_process_spark_submit_log_k8s(self, pod_name):
        # Given
        hook = SparkSubmitHook(conn_id="spark_k8s_cluster")
        log_lines = [
            "INFO  LoggingPodStatusWatcherImpl:54 - State changed, new state:",
            f"pod name: {pod_name}",
            "namespace: default",
            "labels: spark-app-selector -> spark-465b868ada474bda82ccb84ab2747fcd, spark-role -> driver",
            "pod uid: ba9c61f6-205f-11e8-b65f-d48564c88e42",
            "creation time: 2018-03-05T10:26:55Z",
            "service account name: spark",
            "volumes: spark-init-properties, download-jars-volume,download-files-volume, spark-token-2vmlm",
            "node name: N/A",
            "start time: N/A",
            "container images: N/A",
            "phase: Pending",
            "status: []",
            "2018-03-05 11:26:56 INFO  LoggingPodStatusWatcherImpl:54 - State changed, new state:",
            f"pod name: {pod_name}",
            "namespace: default",
            "Exit code: 999",
        ]

        # When
        hook._process_spark_submit_log(log_lines)

        # Then
        assert hook._kubernetes_driver_pod == pod_name
        assert hook._kubernetes_application_id == "spark-465b868ada474bda82ccb84ab2747fcd"
        assert hook._spark_exit_code == 999

    def test_process_spark_submit_log_k8s_spark_3(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_k8s_cluster")
        log_lines = ["exit code: 999"]

        # When
        hook._process_spark_submit_log(log_lines)

        # Then
        assert hook._spark_exit_code == 999

    def test_process_spark_client_mode_submit_log_k8s(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_k8s_client")
        log_lines = [
            "INFO - The executor with id 2 exited with exit code 137(SIGKILL, possible container OOM).",
            "...",
            "Pi is roughly 3.141640",
            "SparkContext: Successfully stopped SparkContext",
        ]

        # When
        hook._process_spark_submit_log(log_lines)

        # Then
        assert hook._spark_exit_code == 0

    def test_process_spark_submit_log_standalone_cluster(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_standalone_cluster")
        log_lines = [
            "Running Spark using the REST application submission protocol.",
            "17/11/28 11:14:15 INFO RestSubmissionClient: Submitting a request "
            "to launch an application in spark://spark-standalone-master:6066",
            "17/11/28 11:14:15 INFO RestSubmissionClient: Submission successfully "
            "created as driver-20171128111415-0001. Polling submission state...",
        ]
        # When
        hook._process_spark_submit_log(log_lines)

        # Then

        assert hook._driver_id == "driver-20171128111415-0001"

    def test_process_spark_driver_status_log(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_standalone_cluster")
        log_lines = [
            "Submitting a request for the status of submission "
            "driver-20171128111415-0001 in spark://spark-standalone-master:6066",
            "17/11/28 11:15:37 INFO RestSubmissionClient: Server responded with SubmissionStatusResponse:",
            "{",
            '"action" : "SubmissionStatusResponse",',
            '"driverState" : "RUNNING",',
            '"serverSparkVersion" : "1.6.0",',
            '"submissionId" : "driver-20171128111415-0001",',
            '"success" : true,',
            '"workerHostPort" : "172.18.0.7:38561",',
            '"workerId" : "worker-20171128110741-172.18.0.7-38561"',
            "}",
        ]
        # When
        hook._process_spark_status_log(log_lines)

        # Then

        assert hook._driver_status == "RUNNING"

    def test_process_spark_driver_status_log_bad_response(self):
        # Given
        hook = SparkSubmitHook(conn_id="spark_standalone_cluster")
        log_lines = [
            "curl: Failed to connect to http://spark-standalone-master:6066This is an invalid Spark response",
            "Timed out",
        ]
        # When
        hook._process_spark_status_log(log_lines)

        # Then

        assert hook._driver_status is None

    @patch("airflow.providers.apache.spark.hooks.spark_submit.renew_from_kt")
    @patch("airflow.providers.apache.spark.hooks.spark_submit.subprocess.Popen")
    def test_yarn_process_on_kill(self, mock_popen, mock_renew_from_kt):
        # Given
        mock_popen.return_value.stdout = StringIO("stdout")
        mock_popen.return_value.stderr = StringIO("stderr")
        mock_popen.return_value.poll.return_value = None
        mock_popen.return_value.wait.return_value = 0
        log_lines = [
            "SPARK_MAJOR_VERSION is set to 2, using Spark2",
            "WARN NativeCodeLoader: Unable to load native-hadoop library for your "
            "platform... using builtin-java classes where applicable",
            "WARN DomainSocketFactory: The short-circuit local reads feature cannot "
            "be used because libhadoop cannot be loaded.",
            "INFO Client: Requesting a new application from cluster with 10 "
            "NodeManagerapplication_1486558679801_1820s",
            "INFO Client: Submitting application application_1486558679801_1820 to ResourceManager",
        ]
        env = {"PATH": "hadoop/bin"}
        hook = SparkSubmitHook(conn_id="spark_yarn_cluster", env_vars=env)
        hook._process_spark_submit_log(log_lines)
        hook.submit()

        # When
        hook.on_kill()

        # Then
        assert (
            call(
                ["yarn", "application", "-kill", "application_1486558679801_1820"],
                env={**os.environ, **env},
                stderr=-1,
                stdout=-1,
            )
            in mock_popen.mock_calls
        )
        # resetting the mock to test  kill with keytab & principal
        mock_popen.reset_mock()
        # Given
        hook = SparkSubmitHook(
            conn_id="spark_yarn_cluster", keytab="privileged_user.keytab", principal="user/spark@airflow.org"
        )
        hook._process_spark_submit_log(log_lines)
        hook.submit()

        # When
        hook.on_kill()
        # Then
        expected_env = os.environ.copy()
        expected_env["KRB5CCNAME"] = "/tmp/airflow_krb5_ccache"
        assert (
            call(
                ["yarn", "application", "-kill", "application_1486558679801_1820"],
                env=expected_env,
                stderr=-1,
                stdout=-1,
            )
            in mock_popen.mock_calls
        )

    def test_standalone_cluster_process_on_kill(self):
        # Given
        log_lines = [
            "Running Spark using the REST application submission protocol.",
            "17/11/28 11:14:15 INFO RestSubmissionClient: Submitting a request "
            "to launch an application in spark://spark-standalone-master:6066",
            "17/11/28 11:14:15 INFO RestSubmissionClient: Submission successfully "
            "created as driver-20171128111415-0001. Polling submission state...",
        ]
        hook = SparkSubmitHook(conn_id="spark_standalone_cluster")
        hook._process_spark_submit_log(log_lines)

        # When
        kill_cmd = hook._build_spark_driver_kill_command()

        # Then
        assert kill_cmd[0] == "spark-submit"
        assert kill_cmd[1] == "--master"
        assert kill_cmd[2] == "spark://spark-standalone-master:6066"
        assert kill_cmd[3] == "--kill"
        assert kill_cmd[4] == "driver-20171128111415-0001"

    @patch("airflow.providers.cncf.kubernetes.kube_client.get_kube_client")
    @patch("airflow.providers.apache.spark.hooks.spark_submit.subprocess.Popen")
    def test_k8s_process_on_kill(self, mock_popen, mock_client_method):
        # Given
        mock_popen.return_value.stdout = StringIO("stdout")
        mock_popen.return_value.stderr = StringIO("stderr")
        mock_popen.return_value.poll.return_value = None
        mock_popen.return_value.wait.return_value = 0
        client = mock_client_method.return_value
        hook = SparkSubmitHook(conn_id="spark_k8s_cluster")
        log_lines = [
            "INFO  LoggingPodStatusWatcherImpl:54 - State changed, new state:",
            "pod name: spark-pi-edf2ace37be7353a958b38733a12f8e6-driver",
            "namespace: default",
            "labels: spark-app-selector -> spark-465b868ada474bda82ccb84ab2747fcd, spark-role -> driver",
            "pod uid: ba9c61f6-205f-11e8-b65f-d48564c88e42",
            "creation time: 2018-03-05T10:26:55Z",
            "service account name: spark",
            "volumes: spark-init-properties, download-jars-volume,download-files-volume, spark-token-2vmlm",
            "node name: N/A",
            "start time: N/A",
            "container images: N/A",
            "phase: Pending",
            "status: []",
            "2018-03-05 11:26:56 INFO  LoggingPodStatusWatcherImpl:54 - State changed, new state:",
            "pod name: spark-pi-edf2ace37be7353a958b38733a12f8e6-driver",
            "namespace: default",
            "Exit code: 0",
        ]
        hook._process_spark_submit_log(log_lines)
        hook.submit()

        # When
        hook.on_kill()

        # Then
        import kubernetes

        kwargs = {"pretty": True, "body": kubernetes.client.V1DeleteOptions()}
        client.delete_namespaced_pod.assert_called_once_with(
            "spark-pi-edf2ace37be7353a958b38733a12f8e6-driver", "mynamespace", **kwargs
        )

    @pytest.mark.parametrize(
        "command, expected",
        [
            (
                ("spark-submit", "foo", "--bar", "baz", "--password='secret'", "--foo", "bar"),
                "spark-submit foo --bar baz --password='******' --foo bar",
            ),
            (
                ("spark-submit", "foo", "--bar", "baz", "--password='secret'"),
                "spark-submit foo --bar baz --password='******'",
            ),
            (
                ("spark-submit", "foo", "--bar", "baz", '--password="secret"'),
                'spark-submit foo --bar baz --password="******"',
            ),
            (
                ("spark-submit", "foo", "--bar", "baz", "--password=secret"),
                "spark-submit foo --bar baz --password=******",
            ),
            (
                ("spark-submit", "foo", "--bar", "baz", "--password 'secret'"),
                "spark-submit foo --bar baz --password '******'",
            ),
            (
                ("spark-submit", "foo", "--bar", "baz", "--password='sec\"ret'"),
                "spark-submit foo --bar baz --password='******'",
            ),
            (
                ("spark-submit", "foo", "--bar", "baz", '--password="sec\'ret"'),
                'spark-submit foo --bar baz --password="******"',
            ),
            (
                ("spark-submit",),
                "spark-submit",
            ),
        ],
    )
    def test_masks_passwords(self, command: str, expected: str) -> None:
        # Given
        hook = SparkSubmitHook()

        # When
        command_masked = hook._mask_cmd(command)

        # Then
        assert command_masked == expected

    def test_create_keytab_path_from_base64_keytab_with_decode_exception(self):
        hook = SparkSubmitHook()
        invalid_base64 = "invalid_base64"

        with pytest.raises(AirflowException, match="Failed to decode base64 keytab"):
            hook._create_keytab_path_from_base64_keytab(invalid_base64, None)

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_keytab_path_from_base64_keytab_with_write_exception(
        self,
        mock_open,
        mock_exists,
    ):
        # Given
        hook = SparkSubmitHook()

        keytab_value = b"abcd"
        base64_keytab = base64.b64encode(keytab_value).decode("UTF-8")
        _mock_open = mock_open()
        _mock_open.write.side_effect = Exception("Write failed")
        mock_exists.return_value = False

        # When
        with pytest.raises(AirflowException, match="Failed to save keytab"):
            hook._create_keytab_path_from_base64_keytab(base64_keytab, None)

        # Then
        assert mock_exists.call_count == 2  # called twice (before write, after write)

    @patch("airflow.providers.apache.spark.hooks.spark_submit.shutil.move")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_keytab_path_from_base64_keytab_with_move_exception(
        self,
        mock_open,
        mock_exists,
        mock_move,
    ):
        # Given
        hook = SparkSubmitHook()

        keytab_value = b"abcd"
        base64_keytab = base64.b64encode(keytab_value).decode("UTF-8")
        mock_exists.return_value = False
        mock_move.side_effect = Exception("Move failed")

        # When
        with pytest.raises(AirflowException, match="Failed to save keytab"):
            hook._create_keytab_path_from_base64_keytab(base64_keytab, None)

        # Then
        mock_open().write.assert_called_once_with(keytab_value)
        mock_move.assert_called_once()
        assert mock_exists.call_count == 2  # called twice (before write, after write)

    @patch("airflow.providers.apache.spark.hooks.spark_submit.uuid.uuid4")
    @patch("pathlib.Path.resolve")
    @patch("airflow.providers.apache.spark.hooks.spark_submit.shutil.move")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_keytab_path_from_base64_keytab_with_new_keytab(
        self,
        mock_open,
        mock_exists,
        mock_move,
        mock_resolve,
        mock_uuid4,
    ):
        # Given
        hook = SparkSubmitHook()

        keytab_value = b"abcd"
        base64_keytab = base64.b64encode(keytab_value).decode("UTF-8")
        mock_uuid4.return_value = "uuid"
        mock_resolve.return_value = Path("resolved_path")
        mock_exists.return_value = False

        # When
        keytab = hook._create_keytab_path_from_base64_keytab(base64_keytab, None)

        # Then
        assert keytab == "resolved_path/airflow_keytab-uuid"
        mock_open().write.assert_called_once_with(keytab_value)
        mock_move.assert_called_once()

    @patch("pathlib.Path.resolve")
    @patch("airflow.providers.apache.spark.hooks.spark_submit.shutil.move")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_keytab_path_from_base64_keytab_with_new_keytab_with_principal(
        self,
        mock_open,
        mock_exists,
        mock_move,
        mock_resolve,
    ):
        # Given
        hook = SparkSubmitHook()

        principal = "user/spark@airflow.org"
        keytab_value = b"abcd"
        base64_keytab = base64.b64encode(keytab_value).decode("UTF-8")
        mock_resolve.return_value = Path("resolved_path")
        mock_exists.return_value = False

        # When
        keytab = hook._create_keytab_path_from_base64_keytab(base64_keytab, principal)

        # Then
        assert keytab == f"resolved_path/airflow_keytab-{principal}"
        mock_open().write.assert_called_once_with(keytab_value)
        mock_move.assert_called_once()

    @patch("pathlib.Path.resolve")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_keytab_path_from_base64_keytab_with_existing_keytab(
        self,
        mock_open,
        mock_exists,
        mock_resolve,
    ):
        # Given
        hook = SparkSubmitHook()

        principal = "user/spark@airflow.org"
        keytab_value = b"abcd"
        base64_keytab = base64.b64encode(keytab_value)
        mock_resolve.return_value = Path("resolved_path")
        mock_exists.return_value = True
        _mock_open = mock_open()
        _mock_open.read.return_value = keytab_value

        # When
        keytab = hook._create_keytab_path_from_base64_keytab(base64_keytab.decode("UTF-8"), principal)

        # Then
        assert keytab == f"resolved_path/airflow_keytab-{principal}"
        mock_open.assert_called_with(Path(f"resolved_path/airflow_keytab-{principal}"), "rb")
        _mock_open.read.assert_called_once()
        assert not _mock_open.write.called, "Keytab file should not be written"

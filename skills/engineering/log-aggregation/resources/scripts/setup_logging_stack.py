#!/usr/bin/env python3
"""
Setup Logging Stack

This script automates the deployment of logging stacks (ELK, EFK, Loki)
with configuration generation, validation, and health checks.

Usage:
    setup_logging_stack.py --stack elk --environment docker
    setup_logging_stack.py --stack loki --environment kubernetes
    setup_logging_stack.py --stack efk --environment docker --validate
    setup_logging_stack.py --stack elk --environment kubernetes --namespace logging --json
"""

import argparse
import sys
import json
import yaml
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import requests


@dataclass
class StackConfig:
    """Configuration for logging stack."""
    stack_type: str  # elk, efk, loki
    environment: str  # docker, kubernetes
    namespace: str = "logging"
    elasticsearch_replicas: int = 1
    elasticsearch_heap_size: str = "2g"
    logstash_heap_size: str = "1g"
    retention_days: int = 30
    storage_size: str = "100Gi"
    enable_security: bool = False


class LoggingStackDeployer:
    """Deploy and configure logging stacks."""

    def __init__(self, config: StackConfig, verbose: bool = False):
        self.config = config
        self.verbose = verbose
        self.output_dir = Path("logging-stack-output")
        self.output_dir.mkdir(exist_ok=True)

    def deploy(self) -> Dict[str, Any]:
        """Deploy the logging stack."""
        self.log("Starting logging stack deployment...")

        result = {
            "stack": self.config.stack_type,
            "environment": self.config.environment,
            "status": "success",
            "components": [],
            "endpoints": {},
            "files_generated": []
        }

        try:
            if self.config.environment == "docker":
                result.update(self._deploy_docker())
            elif self.config.environment == "kubernetes":
                result.update(self._deploy_kubernetes())
            else:
                raise ValueError(f"Unknown environment: {self.config.environment}")

            self.log("Deployment completed successfully")

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            self.log(f"Deployment failed: {e}", error=True)

        return result

    def _deploy_docker(self) -> Dict[str, Any]:
        """Deploy stack using Docker Compose."""
        self.log("Generating Docker Compose configuration...")

        if self.config.stack_type == "elk":
            compose_file = self._generate_elk_docker_compose()
        elif self.config.stack_type == "efk":
            compose_file = self._generate_efk_docker_compose()
        elif self.config.stack_type == "loki":
            compose_file = self._generate_loki_docker_compose()
        else:
            raise ValueError(f"Unknown stack type: {self.config.stack_type}")

        # Write compose file
        compose_path = self.output_dir / "docker-compose.yml"
        with open(compose_path, 'w') as f:
            yaml.dump(compose_file, f, default_flow_style=False)

        self.log(f"Docker Compose file written to: {compose_path}")

        # Generate additional config files
        config_files = self._generate_config_files_docker()

        # Start stack
        self.log("Starting Docker Compose stack...")
        result = subprocess.run(
            ["docker-compose", "-f", str(compose_path), "up", "-d"],
            cwd=self.output_dir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Docker Compose failed: {result.stderr}")

        self.log("Docker Compose stack started")

        return {
            "compose_file": str(compose_path),
            "config_files": config_files,
            "components": self._get_docker_components(),
            "endpoints": self._get_docker_endpoints()
        }

    def _deploy_kubernetes(self) -> Dict[str, Any]:
        """Deploy stack to Kubernetes."""
        self.log("Generating Kubernetes manifests...")

        manifests = []
        if self.config.stack_type == "elk":
            manifests = self._generate_elk_kubernetes_manifests()
        elif self.config.stack_type == "efk":
            manifests = self._generate_efk_kubernetes_manifests()
        elif self.config.stack_type == "loki":
            manifests = self._generate_loki_kubernetes_manifests()
        else:
            raise ValueError(f"Unknown stack type: {self.config.stack_type}")

        # Write manifests
        manifest_files = []
        for name, manifest in manifests:
            manifest_path = self.output_dir / f"{name}.yaml"
            with open(manifest_path, 'w') as f:
                yaml.dump_all(manifest, f, default_flow_style=False)
            manifest_files.append(str(manifest_path))
            self.log(f"Generated manifest: {manifest_path}")

        # Apply manifests
        self.log(f"Applying manifests to Kubernetes namespace: {self.config.namespace}")
        self._create_namespace()

        for manifest_file in manifest_files:
            result = subprocess.run(
                ["kubectl", "apply", "-f", manifest_file, "-n", self.config.namespace],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"kubectl apply failed: {result.stderr}")

        self.log("Kubernetes manifests applied")

        return {
            "namespace": self.config.namespace,
            "manifest_files": manifest_files,
            "components": self._get_kubernetes_components(),
            "endpoints": self._get_kubernetes_endpoints()
        }

    def _generate_elk_docker_compose(self) -> Dict[str, Any]:
        """Generate ELK Stack Docker Compose configuration."""
        return {
            "version": "3.8",
            "services": {
                "elasticsearch": {
                    "image": "docker.elastic.co/elasticsearch/elasticsearch:8.11.0",
                    "container_name": "elasticsearch",
                    "environment": [
                        "node.name=es01",
                        "cluster.name=logs-cluster",
                        "discovery.type=single-node",
                        "bootstrap.memory_lock=true",
                        f"ES_JAVA_OPTS=-Xms{self.config.elasticsearch_heap_size} -Xmx{self.config.elasticsearch_heap_size}",
                        "xpack.security.enabled=false" if not self.config.enable_security else "xpack.security.enabled=true",
                        "xpack.monitoring.collection.enabled=true"
                    ],
                    "ulimits": {
                        "memlock": {"soft": -1, "hard": -1},
                        "nofile": {"soft": 65536, "hard": 65536}
                    },
                    "volumes": ["es_data:/usr/share/elasticsearch/data"],
                    "ports": ["9200:9200", "9300:9300"],
                    "networks": ["elk"]
                },
                "logstash": {
                    "image": "docker.elastic.co/logstash/logstash:8.11.0",
                    "container_name": "logstash",
                    "volumes": [
                        "./logstash/pipeline:/usr/share/logstash/pipeline:ro",
                        "./logstash/config/logstash.yml:/usr/share/logstash/config/logstash.yml:ro"
                    ],
                    "ports": ["5044:5044", "9600:9600"],
                    "environment": [
                        f"LS_JAVA_OPTS=-Xms{self.config.logstash_heap_size} -Xmx{self.config.logstash_heap_size}"
                    ],
                    "networks": ["elk"],
                    "depends_on": ["elasticsearch"]
                },
                "kibana": {
                    "image": "docker.elastic.co/kibana/kibana:8.11.0",
                    "container_name": "kibana",
                    "environment": [
                        "ELASTICSEARCH_HOSTS=http://elasticsearch:9200",
                        "SERVER_NAME=kibana"
                    ],
                    "ports": ["5601:5601"],
                    "networks": ["elk"],
                    "depends_on": ["elasticsearch"]
                },
                "filebeat": {
                    "image": "docker.elastic.co/beats/filebeat:8.11.0",
                    "container_name": "filebeat",
                    "user": "root",
                    "volumes": [
                        "./filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro",
                        "/var/lib/docker/containers:/var/lib/docker/containers:ro",
                        "/var/run/docker.sock:/var/run/docker.sock:ro",
                        "filebeat_data:/usr/share/filebeat/data"
                    ],
                    "command": "filebeat -e -strict.perms=false",
                    "networks": ["elk"],
                    "depends_on": ["logstash"]
                }
            },
            "volumes": {
                "es_data": None,
                "filebeat_data": None
            },
            "networks": {
                "elk": {"driver": "bridge"}
            }
        }

    def _generate_efk_docker_compose(self) -> Dict[str, Any]:
        """Generate EFK Stack Docker Compose configuration."""
        return {
            "version": "3.8",
            "services": {
                "elasticsearch": {
                    "image": "docker.elastic.co/elasticsearch/elasticsearch:8.11.0",
                    "container_name": "elasticsearch",
                    "environment": [
                        "discovery.type=single-node",
                        f"ES_JAVA_OPTS=-Xms{self.config.elasticsearch_heap_size} -Xmx{self.config.elasticsearch_heap_size}",
                        "xpack.security.enabled=false"
                    ],
                    "volumes": ["es_data:/usr/share/elasticsearch/data"],
                    "ports": ["9200:9200"],
                    "networks": ["efk"]
                },
                "fluentd": {
                    "image": "fluent/fluentd:v1-debian-elasticsearch",
                    "container_name": "fluentd",
                    "volumes": [
                        "./fluentd/fluent.conf:/fluentd/etc/fluent.conf:ro",
                        "/var/lib/docker/containers:/var/lib/docker/containers:ro"
                    ],
                    "ports": ["24224:24224", "24224:24224/udp"],
                    "networks": ["efk"],
                    "depends_on": ["elasticsearch"]
                },
                "kibana": {
                    "image": "docker.elastic.co/kibana/kibana:8.11.0",
                    "container_name": "kibana",
                    "environment": ["ELASTICSEARCH_HOSTS=http://elasticsearch:9200"],
                    "ports": ["5601:5601"],
                    "networks": ["efk"],
                    "depends_on": ["elasticsearch"]
                }
            },
            "volumes": {"es_data": None},
            "networks": {"efk": {"driver": "bridge"}}
        }

    def _generate_loki_docker_compose(self) -> Dict[str, Any]:
        """Generate Loki Stack Docker Compose configuration."""
        return {
            "version": "3.8",
            "services": {
                "loki": {
                    "image": "grafana/loki:2.9.3",
                    "container_name": "loki",
                    "ports": ["3100:3100"],
                    "volumes": [
                        "./loki/loki-config.yml:/etc/loki/local-config.yaml:ro",
                        "loki_data:/loki"
                    ],
                    "command": "-config.file=/etc/loki/local-config.yaml",
                    "networks": ["logging"]
                },
                "promtail": {
                    "image": "grafana/promtail:2.9.3",
                    "container_name": "promtail",
                    "volumes": [
                        "/var/log:/var/log:ro",
                        "./promtail/promtail-config.yml:/etc/promtail/config.yml:ro",
                        "/var/lib/docker/containers:/var/lib/docker/containers:ro",
                        "/var/run/docker.sock:/var/run/docker.sock:ro"
                    ],
                    "command": "-config.file=/etc/promtail/config.yml",
                    "networks": ["logging"],
                    "depends_on": ["loki"]
                },
                "grafana": {
                    "image": "grafana/grafana:10.2.2",
                    "container_name": "grafana",
                    "ports": ["3000:3000"],
                    "environment": [
                        "GF_SECURITY_ADMIN_PASSWORD=admin",
                        "GF_USERS_ALLOW_SIGN_UP=false"
                    ],
                    "volumes": [
                        "grafana_data:/var/lib/grafana",
                        "./grafana/datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml:ro"
                    ],
                    "networks": ["logging"],
                    "depends_on": ["loki"]
                }
            },
            "volumes": {
                "loki_data": None,
                "grafana_data": None
            },
            "networks": {
                "logging": {"driver": "bridge"}
            }
        }

    def _generate_config_files_docker(self) -> List[str]:
        """Generate additional configuration files for Docker deployment."""
        config_files = []

        if self.config.stack_type == "elk":
            # Logstash pipeline
            logstash_dir = self.output_dir / "logstash" / "pipeline"
            logstash_dir.mkdir(parents=True, exist_ok=True)

            logstash_conf = """input {
  beats {
    port => 5044
  }
}

filter {
  if [message] =~ /^\\{.*\\}$/ {
    json {
      source => "message"
    }
  }

  date {
    match => ["timestamp", "ISO8601"]
    target => "@timestamp"
  }

  if [level] == "DEBUG" {
    drop {}
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "logs-%{[service]}-%{+YYYY.MM.dd}"
  }
}
"""
            logstash_conf_path = logstash_dir / "logstash.conf"
            with open(logstash_conf_path, 'w') as f:
                f.write(logstash_conf)
            config_files.append(str(logstash_conf_path))

            # Logstash config
            logstash_config_dir = self.output_dir / "logstash" / "config"
            logstash_config_dir.mkdir(parents=True, exist_ok=True)

            logstash_yml = """http.host: "0.0.0.0"
xpack.monitoring.elasticsearch.hosts: ["http://elasticsearch:9200"]
"""
            logstash_yml_path = logstash_config_dir / "logstash.yml"
            with open(logstash_yml_path, 'w') as f:
                f.write(logstash_yml)
            config_files.append(str(logstash_yml_path))

            # Filebeat config
            filebeat_dir = self.output_dir / "filebeat"
            filebeat_dir.mkdir(parents=True, exist_ok=True)

            filebeat_yml = {
                "filebeat.inputs": [
                    {
                        "type": "container",
                        "paths": ["/var/lib/docker/containers/*/*.log"]
                    }
                ],
                "processors": [
                    {"add_host_metadata": None},
                    {"add_docker_metadata": None}
                ],
                "output.logstash": {
                    "hosts": ["logstash:5044"]
                },
                "logging.level": "info"
            }
            filebeat_yml_path = filebeat_dir / "filebeat.yml"
            with open(filebeat_yml_path, 'w') as f:
                yaml.dump(filebeat_yml, f)
            config_files.append(str(filebeat_yml_path))

        elif self.config.stack_type == "efk":
            # Fluentd config
            fluentd_dir = self.output_dir / "fluentd"
            fluentd_dir.mkdir(parents=True, exist_ok=True)

            fluentd_conf = """<source>
  @type forward
  port 24224
  bind 0.0.0.0
</source>

<filter **>
  @type record_transformer
  <record>
    hostname "#{Socket.gethostname}"
  </record>
</filter>

<match **>
  @type elasticsearch
  host elasticsearch
  port 9200
  logstash_format true
  logstash_prefix fluentd
  <buffer>
    @type file
    path /var/log/fluentd-buffers/kubernetes.system.buffer
    flush_mode interval
    flush_interval 5s
    retry_type exponential_backoff
    retry_forever false
    retry_max_interval 30
    chunk_limit_size 2M
    queue_limit_length 8
    overflow_action block
  </buffer>
</match>
"""
            fluentd_conf_path = fluentd_dir / "fluent.conf"
            with open(fluentd_conf_path, 'w') as f:
                f.write(fluentd_conf)
            config_files.append(str(fluentd_conf_path))

        elif self.config.stack_type == "loki":
            # Loki config
            loki_dir = self.output_dir / "loki"
            loki_dir.mkdir(parents=True, exist_ok=True)

            loki_config = {
                "auth_enabled": False,
                "server": {
                    "http_listen_port": 3100,
                    "grpc_listen_port": 9096
                },
                "common": {
                    "path_prefix": "/loki",
                    "storage": {
                        "filesystem": {
                            "chunks_directory": "/loki/chunks",
                            "rules_directory": "/loki/rules"
                        }
                    },
                    "replication_factor": 1,
                    "ring": {
                        "instance_addr": "127.0.0.1",
                        "kvstore": {"store": "inmemory"}
                    }
                },
                "schema_config": {
                    "configs": [
                        {
                            "from": "2020-10-24",
                            "store": "boltdb-shipper",
                            "object_store": "filesystem",
                            "schema": "v11",
                            "index": {
                                "prefix": "index_",
                                "period": "24h"
                            }
                        }
                    ]
                },
                "limits_config": {
                    "retention_period": f"{self.config.retention_days * 24}h",
                    "ingestion_rate_mb": 10,
                    "ingestion_burst_size_mb": 20
                },
                "table_manager": {
                    "retention_deletes_enabled": True,
                    "retention_period": f"{self.config.retention_days * 24}h"
                }
            }
            loki_config_path = loki_dir / "loki-config.yml"
            with open(loki_config_path, 'w') as f:
                yaml.dump(loki_config, f)
            config_files.append(str(loki_config_path))

            # Promtail config
            promtail_dir = self.output_dir / "promtail"
            promtail_dir.mkdir(parents=True, exist_ok=True)

            promtail_config = {
                "server": {
                    "http_listen_port": 9080,
                    "grpc_listen_port": 0
                },
                "positions": {
                    "filename": "/tmp/positions.yaml"
                },
                "clients": [
                    {"url": "http://loki:3100/loki/api/v1/push"}
                ],
                "scrape_configs": [
                    {
                        "job_name": "containers",
                        "docker_sd_configs": [
                            {
                                "host": "unix:///var/run/docker.sock",
                                "refresh_interval": "5s"
                            }
                        ],
                        "relabel_configs": [
                            {
                                "source_labels": ["__meta_docker_container_name"],
                                "regex": "/(.*)",
                                "target_label": "container"
                            }
                        ]
                    }
                ]
            }
            promtail_config_path = promtail_dir / "promtail-config.yml"
            with open(promtail_config_path, 'w') as f:
                yaml.dump(promtail_config, f)
            config_files.append(str(promtail_config_path))

            # Grafana datasource
            grafana_dir = self.output_dir / "grafana"
            grafana_dir.mkdir(parents=True, exist_ok=True)

            grafana_datasource = {
                "apiVersion": 1,
                "datasources": [
                    {
                        "name": "Loki",
                        "type": "loki",
                        "access": "proxy",
                        "url": "http://loki:3100",
                        "isDefault": True,
                        "editable": True
                    }
                ]
            }
            grafana_datasource_path = grafana_dir / "datasources.yml"
            with open(grafana_datasource_path, 'w') as f:
                yaml.dump(grafana_datasource, f)
            config_files.append(str(grafana_datasource_path))

        return config_files

    def _generate_elk_kubernetes_manifests(self) -> List[Tuple[str, List[Dict[str, Any]]]]:
        """Generate ELK Stack Kubernetes manifests."""
        manifests = []

        # Elasticsearch StatefulSet
        elasticsearch_manifest = [
            {
                "apiVersion": "apps/v1",
                "kind": "StatefulSet",
                "metadata": {
                    "name": "elasticsearch",
                    "namespace": self.config.namespace
                },
                "spec": {
                    "serviceName": "elasticsearch",
                    "replicas": self.config.elasticsearch_replicas,
                    "selector": {
                        "matchLabels": {"app": "elasticsearch"}
                    },
                    "template": {
                        "metadata": {
                            "labels": {"app": "elasticsearch"}
                        },
                        "spec": {
                            "containers": [
                                {
                                    "name": "elasticsearch",
                                    "image": "docker.elastic.co/elasticsearch/elasticsearch:8.11.0",
                                    "resources": {
                                        "requests": {"memory": "4Gi", "cpu": "1000m"},
                                        "limits": {"memory": "8Gi", "cpu": "2000m"}
                                    },
                                    "ports": [
                                        {"containerPort": 9200, "name": "http"},
                                        {"containerPort": 9300, "name": "transport"}
                                    ],
                                    "env": [
                                        {"name": "cluster.name", "value": "k8s-logs"},
                                        {"name": "node.name", "valueFrom": {"fieldRef": {"fieldPath": "metadata.name"}}},
                                        {"name": "discovery.type", "value": "single-node"},
                                        {"name": "ES_JAVA_OPTS", "value": f"-Xms{self.config.elasticsearch_heap_size} -Xmx{self.config.elasticsearch_heap_size}"}
                                    ],
                                    "volumeMounts": [
                                        {"name": "data", "mountPath": "/usr/share/elasticsearch/data"}
                                    ]
                                }
                            ]
                        }
                    },
                    "volumeClaimTemplates": [
                        {
                            "metadata": {"name": "data"},
                            "spec": {
                                "accessModes": ["ReadWriteOnce"],
                                "resources": {
                                    "requests": {"storage": self.config.storage_size}
                                }
                            }
                        }
                    ]
                }
            },
            {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "name": "elasticsearch",
                    "namespace": self.config.namespace
                },
                "spec": {
                    "selector": {"app": "elasticsearch"},
                    "ports": [
                        {"port": 9200, "name": "http"},
                        {"port": 9300, "name": "transport"}
                    ]
                }
            }
        ]
        manifests.append(("elasticsearch", elasticsearch_manifest))

        # Kibana Deployment
        kibana_manifest = [
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": "kibana",
                    "namespace": self.config.namespace
                },
                "spec": {
                    "replicas": 1,
                    "selector": {
                        "matchLabels": {"app": "kibana"}
                    },
                    "template": {
                        "metadata": {
                            "labels": {"app": "kibana"}
                        },
                        "spec": {
                            "containers": [
                                {
                                    "name": "kibana",
                                    "image": "docker.elastic.co/kibana/kibana:8.11.0",
                                    "ports": [{"containerPort": 5601}],
                                    "env": [
                                        {"name": "ELASTICSEARCH_HOSTS", "value": "http://elasticsearch:9200"}
                                    ]
                                }
                            ]
                        }
                    }
                }
            },
            {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "name": "kibana",
                    "namespace": self.config.namespace
                },
                "spec": {
                    "selector": {"app": "kibana"},
                    "ports": [{"port": 5601}],
                    "type": "LoadBalancer"
                }
            }
        ]
        manifests.append(("kibana", kibana_manifest))

        # Filebeat DaemonSet
        filebeat_manifest = [
            {
                "apiVersion": "v1",
                "kind": "ServiceAccount",
                "metadata": {
                    "name": "filebeat",
                    "namespace": self.config.namespace
                }
            },
            {
                "apiVersion": "apps/v1",
                "kind": "DaemonSet",
                "metadata": {
                    "name": "filebeat",
                    "namespace": self.config.namespace
                },
                "spec": {
                    "selector": {
                        "matchLabels": {"app": "filebeat"}
                    },
                    "template": {
                        "metadata": {
                            "labels": {"app": "filebeat"}
                        },
                        "spec": {
                            "serviceAccountName": "filebeat",
                            "containers": [
                                {
                                    "name": "filebeat",
                                    "image": "docker.elastic.co/beats/filebeat:8.11.0",
                                    "args": ["-c", "/etc/filebeat.yml", "-e"],
                                    "volumeMounts": [
                                        {"name": "varlog", "mountPath": "/var/log", "readOnly": True},
                                        {"name": "varlibdockercontainers", "mountPath": "/var/lib/docker/containers", "readOnly": True}
                                    ]
                                }
                            ],
                            "volumes": [
                                {"name": "varlog", "hostPath": {"path": "/var/log"}},
                                {"name": "varlibdockercontainers", "hostPath": {"path": "/var/lib/docker/containers"}}
                            ]
                        }
                    }
                }
            }
        ]
        manifests.append(("filebeat", filebeat_manifest))

        return manifests

    def _generate_efk_kubernetes_manifests(self) -> List[Tuple[str, List[Dict[str, Any]]]]:
        """Generate EFK Stack Kubernetes manifests."""
        manifests = []

        # Elasticsearch (reuse from ELK)
        elk_manifests = self._generate_elk_kubernetes_manifests()
        manifests.append(elk_manifests[0])  # Elasticsearch
        manifests.append(elk_manifests[1])  # Kibana

        # Fluentd DaemonSet
        fluentd_manifest = [
            {
                "apiVersion": "v1",
                "kind": "ServiceAccount",
                "metadata": {
                    "name": "fluentd",
                    "namespace": self.config.namespace
                }
            },
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "ClusterRole",
                "metadata": {"name": "fluentd"},
                "rules": [
                    {
                        "apiGroups": [""],
                        "resources": ["pods", "namespaces"],
                        "verbs": ["get", "list", "watch"]
                    }
                ]
            },
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "ClusterRoleBinding",
                "metadata": {"name": "fluentd"},
                "roleRef": {
                    "kind": "ClusterRole",
                    "name": "fluentd",
                    "apiGroup": "rbac.authorization.k8s.io"
                },
                "subjects": [
                    {
                        "kind": "ServiceAccount",
                        "name": "fluentd",
                        "namespace": self.config.namespace
                    }
                ]
            },
            {
                "apiVersion": "apps/v1",
                "kind": "DaemonSet",
                "metadata": {
                    "name": "fluentd",
                    "namespace": self.config.namespace
                },
                "spec": {
                    "selector": {
                        "matchLabels": {"app": "fluentd"}
                    },
                    "template": {
                        "metadata": {
                            "labels": {"app": "fluentd"}
                        },
                        "spec": {
                            "serviceAccountName": "fluentd",
                            "containers": [
                                {
                                    "name": "fluentd",
                                    "image": "fluent/fluentd-kubernetes-daemonset:v1-debian-elasticsearch",
                                    "env": [
                                        {"name": "FLUENT_ELASTICSEARCH_HOST", "value": "elasticsearch"},
                                        {"name": "FLUENT_ELASTICSEARCH_PORT", "value": "9200"}
                                    ],
                                    "resources": {
                                        "limits": {"memory": "512Mi"},
                                        "requests": {"cpu": "100m", "memory": "256Mi"}
                                    },
                                    "volumeMounts": [
                                        {"name": "varlog", "mountPath": "/var/log"},
                                        {"name": "varlibdockercontainers", "mountPath": "/var/lib/docker/containers", "readOnly": True}
                                    ]
                                }
                            ],
                            "volumes": [
                                {"name": "varlog", "hostPath": {"path": "/var/log"}},
                                {"name": "varlibdockercontainers", "hostPath": {"path": "/var/lib/docker/containers"}}
                            ]
                        }
                    }
                }
            }
        ]
        manifests.append(("fluentd", fluentd_manifest))

        return manifests

    def _generate_loki_kubernetes_manifests(self) -> List[Tuple[str, List[Dict[str, Any]]]]:
        """Generate Loki Stack Kubernetes manifests."""
        manifests = []

        # Loki StatefulSet
        loki_manifest = [
            {
                "apiVersion": "apps/v1",
                "kind": "StatefulSet",
                "metadata": {
                    "name": "loki",
                    "namespace": self.config.namespace
                },
                "spec": {
                    "serviceName": "loki",
                    "replicas": 1,
                    "selector": {
                        "matchLabels": {"app": "loki"}
                    },
                    "template": {
                        "metadata": {
                            "labels": {"app": "loki"}
                        },
                        "spec": {
                            "containers": [
                                {
                                    "name": "loki",
                                    "image": "grafana/loki:2.9.3",
                                    "ports": [{"containerPort": 3100, "name": "http"}],
                                    "volumeMounts": [
                                        {"name": "storage", "mountPath": "/loki"}
                                    ],
                                    "resources": {
                                        "requests": {"cpu": "500m", "memory": "1Gi"},
                                        "limits": {"cpu": "1000m", "memory": "2Gi"}
                                    }
                                }
                            ]
                        }
                    },
                    "volumeClaimTemplates": [
                        {
                            "metadata": {"name": "storage"},
                            "spec": {
                                "accessModes": ["ReadWriteOnce"],
                                "resources": {
                                    "requests": {"storage": self.config.storage_size}
                                }
                            }
                        }
                    ]
                }
            },
            {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "name": "loki",
                    "namespace": self.config.namespace
                },
                "spec": {
                    "selector": {"app": "loki"},
                    "ports": [{"port": 3100, "name": "http"}]
                }
            }
        ]
        manifests.append(("loki", loki_manifest))

        # Grafana Deployment
        grafana_manifest = [
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": "grafana",
                    "namespace": self.config.namespace
                },
                "spec": {
                    "replicas": 1,
                    "selector": {
                        "matchLabels": {"app": "grafana"}
                    },
                    "template": {
                        "metadata": {
                            "labels": {"app": "grafana"}
                        },
                        "spec": {
                            "containers": [
                                {
                                    "name": "grafana",
                                    "image": "grafana/grafana:10.2.2",
                                    "ports": [{"containerPort": 3000}],
                                    "env": [
                                        {"name": "GF_SECURITY_ADMIN_PASSWORD", "value": "admin"}
                                    ]
                                }
                            ]
                        }
                    }
                }
            },
            {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "name": "grafana",
                    "namespace": self.config.namespace
                },
                "spec": {
                    "selector": {"app": "grafana"},
                    "ports": [{"port": 3000}],
                    "type": "LoadBalancer"
                }
            }
        ]
        manifests.append(("grafana", grafana_manifest))

        return manifests

    def _create_namespace(self) -> None:
        """Create Kubernetes namespace if it doesn't exist."""
        result = subprocess.run(
            ["kubectl", "get", "namespace", self.config.namespace],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            self.log(f"Creating namespace: {self.config.namespace}")
            subprocess.run(
                ["kubectl", "create", "namespace", self.config.namespace],
                check=True
            )

    def _get_docker_components(self) -> List[str]:
        """Get list of Docker components."""
        if self.config.stack_type == "elk":
            return ["elasticsearch", "logstash", "kibana", "filebeat"]
        elif self.config.stack_type == "efk":
            return ["elasticsearch", "fluentd", "kibana"]
        elif self.config.stack_type == "loki":
            return ["loki", "promtail", "grafana"]
        return []

    def _get_docker_endpoints(self) -> Dict[str, str]:
        """Get Docker endpoints."""
        endpoints = {}
        if self.config.stack_type in ["elk", "efk"]:
            endpoints["elasticsearch"] = "http://localhost:9200"
            endpoints["kibana"] = "http://localhost:5601"
        elif self.config.stack_type == "loki":
            endpoints["loki"] = "http://localhost:3100"
            endpoints["grafana"] = "http://localhost:3000"
        return endpoints

    def _get_kubernetes_components(self) -> List[str]:
        """Get list of Kubernetes components."""
        return self._get_docker_components()

    def _get_kubernetes_endpoints(self) -> Dict[str, str]:
        """Get Kubernetes endpoints (kubectl port-forward instructions)."""
        endpoints = {}
        ns = self.config.namespace
        if self.config.stack_type in ["elk", "efk"]:
            endpoints["elasticsearch"] = f"kubectl port-forward -n {ns} svc/elasticsearch 9200:9200"
            endpoints["kibana"] = f"kubectl port-forward -n {ns} svc/kibana 5601:5601"
        elif self.config.stack_type == "loki":
            endpoints["loki"] = f"kubectl port-forward -n {ns} svc/loki 3100:3100"
            endpoints["grafana"] = f"kubectl port-forward -n {ns} svc/grafana 3000:3000"
        return endpoints

    def validate(self) -> Dict[str, Any]:
        """Validate the deployed stack."""
        self.log("Validating logging stack...")

        result = {
            "status": "success",
            "checks": []
        }

        if self.config.environment == "docker":
            result["checks"] = self._validate_docker()
        elif self.config.environment == "kubernetes":
            result["checks"] = self._validate_kubernetes()

        failed_checks = [c for c in result["checks"] if not c["passed"]]
        if failed_checks:
            result["status"] = "failed"

        return result

    def _validate_docker(self) -> List[Dict[str, Any]]:
        """Validate Docker deployment."""
        checks = []

        for component in self._get_docker_components():
            check = {
                "component": component,
                "check": "container_running",
                "passed": False,
                "message": ""
            }

            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={component}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True
            )

            if component in result.stdout:
                check["passed"] = True
                check["message"] = f"{component} is running"
            else:
                check["message"] = f"{component} is not running"

            checks.append(check)

        # Check endpoints
        if self.config.stack_type in ["elk", "efk"]:
            checks.append(self._check_http_endpoint("elasticsearch", "http://localhost:9200"))
            checks.append(self._check_http_endpoint("kibana", "http://localhost:5601"))
        elif self.config.stack_type == "loki":
            checks.append(self._check_http_endpoint("loki", "http://localhost:3100/ready"))
            checks.append(self._check_http_endpoint("grafana", "http://localhost:3000"))

        return checks

    def _validate_kubernetes(self) -> List[Dict[str, Any]]:
        """Validate Kubernetes deployment."""
        checks = []

        for component in self._get_kubernetes_components():
            check = {
                "component": component,
                "check": "pod_ready",
                "passed": False,
                "message": ""
            }

            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", self.config.namespace,
                 "-l", f"app={component}", "-o", "jsonpath={.items[0].status.phase}"],
                capture_output=True,
                text=True
            )

            if "Running" in result.stdout:
                check["passed"] = True
                check["message"] = f"{component} pod is running"
            else:
                check["message"] = f"{component} pod is not running: {result.stdout}"

            checks.append(check)

        return checks

    def _check_http_endpoint(self, name: str, url: str, timeout: int = 5) -> Dict[str, Any]:
        """Check if HTTP endpoint is accessible."""
        check = {
            "component": name,
            "check": "http_endpoint",
            "passed": False,
            "message": ""
        }

        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code < 500:
                check["passed"] = True
                check["message"] = f"{name} endpoint is accessible"
            else:
                check["message"] = f"{name} endpoint returned {response.status_code}"
        except Exception as e:
            check["message"] = f"{name} endpoint not accessible: {str(e)}"

        return check

    def log(self, message: str, error: bool = False) -> None:
        """Log a message."""
        if self.verbose or error:
            prefix = "ERROR" if error else "INFO"
            print(f"[{prefix}] {message}", file=sys.stderr if error else sys.stdout)


def main():
    parser = argparse.ArgumentParser(
        description="Setup logging stack (ELK, EFK, Loki)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy ELK stack with Docker Compose
  setup_logging_stack.py --stack elk --environment docker

  # Deploy Loki to Kubernetes
  setup_logging_stack.py --stack loki --environment kubernetes

  # Deploy and validate
  setup_logging_stack.py --stack elk --environment docker --validate

  # JSON output
  setup_logging_stack.py --stack loki --environment docker --json
        """
    )

    parser.add_argument("--stack", required=True, choices=["elk", "efk", "loki"],
                        help="Logging stack to deploy")
    parser.add_argument("--environment", required=True, choices=["docker", "kubernetes"],
                        help="Deployment environment")
    parser.add_argument("--namespace", default="logging",
                        help="Kubernetes namespace (default: logging)")
    parser.add_argument("--elasticsearch-replicas", type=int, default=1,
                        help="Number of Elasticsearch replicas (default: 1)")
    parser.add_argument("--elasticsearch-heap-size", default="2g",
                        help="Elasticsearch heap size (default: 2g)")
    parser.add_argument("--logstash-heap-size", default="1g",
                        help="Logstash heap size (default: 1g)")
    parser.add_argument("--retention-days", type=int, default=30,
                        help="Log retention in days (default: 30)")
    parser.add_argument("--storage-size", default="100Gi",
                        help="Storage size for persistent volumes (default: 100Gi)")
    parser.add_argument("--enable-security", action="store_true",
                        help="Enable security features (X-Pack)")
    parser.add_argument("--validate", action="store_true",
                        help="Validate deployment after setup")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    parser.add_argument("--verbose", action="store_true",
                        help="Verbose output")

    args = parser.parse_args()

    config = StackConfig(
        stack_type=args.stack,
        environment=args.environment,
        namespace=args.namespace,
        elasticsearch_replicas=args.elasticsearch_replicas,
        elasticsearch_heap_size=args.elasticsearch_heap_size,
        logstash_heap_size=args.logstash_heap_size,
        retention_days=args.retention_days,
        storage_size=args.storage_size,
        enable_security=args.enable_security
    )

    deployer = LoggingStackDeployer(config, verbose=args.verbose)

    # Deploy stack
    result = deployer.deploy()

    # Validate if requested
    if args.validate and result["status"] == "success":
        deployer.log("Waiting for services to start...")
        time.sleep(10)
        validation_result = deployer.validate()
        result["validation"] = validation_result

    # Output results
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\nDeployment Status: {result['status']}")
        print(f"Stack: {result['stack']}")
        print(f"Environment: {result['environment']}")

        if result.get("endpoints"):
            print("\nEndpoints:")
            for name, url in result["endpoints"].items():
                print(f"  {name}: {url}")

        if args.validate and "validation" in result:
            print("\nValidation Results:")
            for check in result["validation"]["checks"]:
                status = "✓" if check["passed"] else "✗"
                print(f"  {status} {check['component']}: {check['message']}")

        if result["status"] == "failed":
            print(f"\nError: {result.get('error', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)

    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()

"""Plugin development examples for Claude Code Builder."""
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import yaml


class PluginExample:
    """Examples of Claude Code Builder plugins."""
    
    @staticmethod
    def get_all_examples() -> Dict[str, str]:
        """Get all plugin examples.
        
        Returns:
            Dictionary of plugin examples
        """
        return {
            'basic_plugin': PluginExample.basic_plugin_example(),
            'build_notifier': PluginExample.build_notifier_plugin(),
            'code_analyzer': PluginExample.code_analyzer_plugin(),
            'deployment_plugin': PluginExample.deployment_plugin(),
            'test_runner': PluginExample.test_runner_plugin(),
            'documentation_plugin': PluginExample.documentation_plugin(),
            'metrics_collector': PluginExample.metrics_collector_plugin(),
            'security_scanner': PluginExample.security_scanner_plugin()
        }
    
    @staticmethod
    def basic_plugin_example() -> str:
        """Basic plugin structure example.
        
        Returns:
            Plugin code
        """
        return '''"""Basic Claude Code Builder plugin example."""
from claude_code_builder.cli.plugins import Plugin, PluginHook
from pathlib import Path
from typing import Dict, Any, Optional
import logging


class BasicPlugin(Plugin):
    """A basic example plugin demonstrating core functionality."""
    
    # Plugin metadata
    name = "basic_plugin"
    version = "1.0.0"
    description = "Basic example plugin for Claude Code Builder"
    author = "Your Name"
    
    def __init__(self):
        """Initialize the plugin."""
        super().__init__()
        self.builds_processed = 0
        self.logger = logging.getLogger(f"plugin.{self.name}")
    
    def on_load(self, context: Dict[str, Any]) -> None:
        """Called when plugin is loaded.
        
        Args:
            context: Plugin context with configuration
        """
        self.logger.info(f"{self.name} plugin loaded successfully")
        
        # Access plugin configuration
        config = context.get('config', {})
        self.debug_mode = config.get('debug', False)
        
        if self.debug_mode:
            self.logger.setLevel(logging.DEBUG)
    
    def on_pre_build(self, context: Dict[str, Any]) -> None:
        """Called before build starts.
        
        Args:
            context: Build context
        """
        project = context['project']
        output_dir = context['output_dir']
        
        self.logger.info(f"Starting build for project: {project.name}")
        self.logger.info(f"Output directory: {output_dir}")
        
        # You can modify the context here
        context['plugin_data'] = {
            'start_time': self._get_timestamp(),
            'project_size': self._estimate_project_size(project)
        }
    
    def on_pre_phase(self, context: Dict[str, Any]) -> None:
        """Called before each phase starts.
        
        Args:
            context: Phase context
        """
        phase = context['phase']
        phase_number = context['phase_number']
        total_phases = context['total_phases']
        
        self.logger.info(f"Starting phase {phase_number}/{total_phases}: {phase.name}")
        
        # Example: Skip certain phases based on configuration
        if self.debug_mode and phase.name == "Testing":
            self.logger.warning("Skipping testing phase in debug mode")
            context['skip_phase'] = True
    
    def on_post_phase(self, context: Dict[str, Any]) -> None:
        """Called after each phase completes.
        
        Args:
            context: Phase context
        """
        phase = context['phase']
        duration = context.get('phase_duration', 0)
        
        self.logger.info(f"Completed phase: {phase.name} in {duration:.2f}s")
        
        # Collect metrics
        if 'metrics' not in context:
            context['metrics'] = {}
        
        context['metrics'][phase.name] = {
            'duration': duration,
            'files_created': len(context.get('created_files', []))
        }
    
    def on_build_complete(self, context: Dict[str, Any]) -> None:
        """Called when build completes successfully.
        
        Args:
            context: Build context
        """
        self.builds_processed += 1
        output_dir = Path(context['output_dir'])
        
        # Generate summary report
        report = self._generate_build_report(context)
        report_path = output_dir / 'build-report.json'
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Build complete! Report saved to: {report_path}")
    
    def on_build_failed(self, context: Dict[str, Any]) -> None:
        """Called when build fails.
        
        Args:
            context: Build context with error information
        """
        error = context.get('error', 'Unknown error')
        phase = context.get('failed_phase', 'Unknown')
        
        self.logger.error(f"Build failed in phase: {phase}")
        self.logger.error(f"Error: {error}")
        
        # Could send notifications, save error report, etc.
    
    def on_unload(self) -> None:
        """Called when plugin is unloaded."""
        self.logger.info(f"Unloading {self.name} plugin")
        self.logger.info(f"Total builds processed: {self.builds_processed}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _estimate_project_size(self, project: Any) -> str:
        """Estimate project size based on phases."""
        phase_count = len(project.phases)
        if phase_count < 5:
            return "small"
        elif phase_count < 10:
            return "medium"
        else:
            return "large"
    
    def _generate_build_report(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate build report."""
        plugin_data = context.get('plugin_data', {})
        metrics = context.get('metrics', {})
        
        total_duration = sum(m.get('duration', 0) for m in metrics.values())
        total_files = sum(m.get('files_created', 0) for m in metrics.values())
        
        return {
            'plugin': self.name,
            'version': self.version,
            'build_info': {
                'start_time': plugin_data.get('start_time'),
                'end_time': self._get_timestamp(),
                'total_duration': total_duration,
                'project_size': plugin_data.get('project_size')
            },
            'metrics': metrics,
            'summary': {
                'total_phases': len(metrics),
                'total_files_created': total_files,
                'average_phase_duration': total_duration / len(metrics) if metrics else 0
            }
        }


# Plugin registration
def register():
    """Register the plugin."""
    return BasicPlugin()
'''
    
    @staticmethod
    def build_notifier_plugin() -> str:
        """Build notification plugin example.
        
        Returns:
            Plugin code
        """
        return '''"""Build notification plugin for Claude Code Builder."""
from claude_code_builder.cli.plugins import Plugin
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from typing import Dict, Any
import os


class BuildNotifierPlugin(Plugin):
    """Send notifications on build events."""
    
    name = "build_notifier"
    version = "1.0.0"
    description = "Sends notifications via email, Slack, or webhooks"
    
    def on_load(self, context: Dict[str, Any]) -> None:
        """Configure notification settings."""
        config = context.get('config', {})
        
        # Email settings
        self.email_enabled = config.get('email', {}).get('enabled', False)
        self.email_to = config.get('email', {}).get('to', [])
        self.smtp_host = config.get('email', {}).get('smtp_host', 'localhost')
        self.smtp_port = config.get('email', {}).get('smtp_port', 587)
        self.smtp_user = config.get('email', {}).get('smtp_user')
        self.smtp_pass = config.get('email', {}).get('smtp_pass')
        
        # Slack settings
        self.slack_enabled = config.get('slack', {}).get('enabled', False)
        self.slack_webhook = config.get('slack', {}).get('webhook_url')
        self.slack_channel = config.get('slack', {}).get('channel', '#builds')
        
        # Generic webhook
        self.webhook_enabled = config.get('webhook', {}).get('enabled', False)
        self.webhook_url = config.get('webhook', {}).get('url')
        self.webhook_headers = config.get('webhook', {}).get('headers', {})
    
    def on_pre_build(self, context: Dict[str, Any]) -> None:
        """Notify build start."""
        project = context['project']
        message = f"🚀 Build started for project: {project.name}"
        
        self._send_notifications(
            subject=f"Build Started: {project.name}",
            message=message,
            context=context
        )
    
    def on_build_complete(self, context: Dict[str, Any]) -> None:
        """Notify build success."""
        project = context['project']
        duration = context.get('total_duration', 0)
        
        message = f"""✅ Build completed successfully!

Project: {project.name}
Duration: {duration:.2f} seconds
Output: {context['output_dir']}
"""
        
        self._send_notifications(
            subject=f"Build Success: {project.name}",
            message=message,
            context=context,
            notification_type='success'
        )
    
    def on_build_failed(self, context: Dict[str, Any]) -> None:
        """Notify build failure."""
        project = context.get('project')
        error = context.get('error', 'Unknown error')
        phase = context.get('failed_phase', 'Unknown')
        
        message = f"""❌ Build failed!

Project: {project.name if project else 'Unknown'}
Phase: {phase}
Error: {error}
"""
        
        self._send_notifications(
            subject=f"Build Failed: {project.name if project else 'Unknown'}",
            message=message,
            context=context,
            notification_type='error'
        )
    
    def _send_notifications(
        self,
        subject: str,
        message: str,
        context: Dict[str, Any],
        notification_type: str = 'info'
    ) -> None:
        """Send notifications to all configured channels."""
        if self.email_enabled:
            self._send_email(subject, message)
        
        if self.slack_enabled:
            self._send_slack(message, notification_type)
        
        if self.webhook_enabled:
            self._send_webhook(subject, message, context, notification_type)
    
    def _send_email(self, subject: str, message: str) -> None:
        """Send email notification."""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = ', '.join(self.email_to)
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'plain'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_pass:
                    server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
                
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
    
    def _send_slack(self, message: str, notification_type: str) -> None:
        """Send Slack notification."""
        try:
            color_map = {
                'info': '#36a64f',
                'success': '#36a64f',
                'error': '#ff0000',
                'warning': '#ff9900'
            }
            
            payload = {
                'channel': self.slack_channel,
                'attachments': [{
                    'color': color_map.get(notification_type, '#36a64f'),
                    'text': message,
                    'footer': 'Claude Code Builder',
                    'ts': int(time.time())
                }]
            }
            
            response = requests.post(self.slack_webhook, json=payload)
            response.raise_for_status()
            
        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {e}")
    
    def _send_webhook(
        self,
        subject: str,
        message: str,
        context: Dict[str, Any],
        notification_type: str
    ) -> None:
        """Send generic webhook notification."""
        try:
            payload = {
                'event': 'build_notification',
                'type': notification_type,
                'subject': subject,
                'message': message,
                'project': context.get('project', {}).name if context.get('project') else None,
                'timestamp': self._get_timestamp()
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=self.webhook_headers
            )
            response.raise_for_status()
            
        except Exception as e:
            self.logger.error(f"Failed to send webhook: {e}")


def register():
    """Register the plugin."""
    return BuildNotifierPlugin()
'''
    
    @staticmethod
    def code_analyzer_plugin() -> str:
        """Code analysis plugin example.
        
        Returns:
            Plugin code
        """
        return '''"""Code analyzer plugin for Claude Code Builder."""
from claude_code_builder.cli.plugins import Plugin
from pathlib import Path
from typing import Dict, Any, List, Tuple
import ast
import re
from collections import defaultdict


class CodeAnalyzerPlugin(Plugin):
    """Analyze generated code for quality and patterns."""
    
    name = "code_analyzer"
    version = "1.0.0"
    description = "Analyzes generated code for quality metrics and patterns"
    
    def __init__(self):
        """Initialize analyzer."""
        super().__init__()
        self.metrics = defaultdict(int)
        self.issues = []
        self.patterns = []
    
    def on_post_phase(self, context: Dict[str, Any]) -> None:
        """Analyze code after each phase."""
        phase = context['phase']
        created_files = context.get('created_files', [])
        
        self.logger.info(f"Analyzing {len(created_files)} files from phase: {phase.name}")
        
        for file_path in created_files:
            if file_path.endswith('.py'):
                self._analyze_python_file(file_path)
            elif file_path.endswith(('.js', '.ts')):
                self._analyze_javascript_file(file_path)
    
    def on_build_complete(self, context: Dict[str, Any]) -> None:
        """Generate analysis report."""
        output_dir = Path(context['output_dir'])
        
        report = self._generate_analysis_report()
        report_path = output_dir / 'code-analysis-report.md'
        
        report_path.write_text(report)
        self.logger.info(f"Code analysis report saved to: {report_path}")
        
        # Display summary
        self._display_summary()
    
    def _analyze_python_file(self, file_path: str) -> None:
        """Analyze Python file."""
        try:
            path = Path(file_path)
            content = path.read_text()
            
            # Basic metrics
            lines = content.split('\\n')
            self.metrics['total_lines'] += len(lines)
            self.metrics['code_lines'] += sum(1 for line in lines if line.strip() and not line.strip().startswith('#'))
            self.metrics['comment_lines'] += sum(1 for line in lines if line.strip().startswith('#'))
            self.metrics['blank_lines'] += sum(1 for line in lines if not line.strip())
            
            # Parse AST
            tree = ast.parse(content)
            
            # Count constructs
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    self.metrics['functions'] += 1
                    self._check_function_complexity(node, file_path)
                elif isinstance(node, ast.ClassDef):
                    self.metrics['classes'] += 1
                elif isinstance(node, ast.Import):
                    self.metrics['imports'] += 1
            
            # Check for patterns and issues
            self._check_code_patterns(content, file_path)
            
        except Exception as e:
            self.logger.error(f"Error analyzing {file_path}: {e}")
    
    def _analyze_javascript_file(self, file_path: str) -> None:
        """Analyze JavaScript/TypeScript file."""
        try:
            path = Path(file_path)
            content = path.read_text()
            
            # Basic metrics
            lines = content.split('\\n')
            self.metrics['total_lines'] += len(lines)
            
            # Simple pattern matching for JS
            self.metrics['functions'] += len(re.findall(r'function\\s+\\w+', content))
            self.metrics['functions'] += len(re.findall(r'\\w+\\s*=\\s*\\([^)]*\\)\\s*=>', content))
            self.metrics['classes'] += len(re.findall(r'class\\s+\\w+', content))
            
        except Exception as e:
            self.logger.error(f"Error analyzing {file_path}: {e}")
    
    def _check_function_complexity(self, node: ast.FunctionDef, file_path: str) -> None:
        """Check function complexity."""
        # Simple cyclomatic complexity
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
        
        if complexity > 10:
            self.issues.append({
                'file': file_path,
                'line': node.lineno,
                'type': 'complexity',
                'message': f'Function {node.name} has high complexity: {complexity}'
            })
        
        self.metrics['total_complexity'] += complexity
    
    def _check_code_patterns(self, content: str, file_path: str) -> None:
        """Check for code patterns and potential issues."""
        lines = content.split('\\n')
        
        for i, line in enumerate(lines, 1):
            # Check for common issues
            if 'TODO' in line or 'FIXME' in line:
                self.issues.append({
                    'file': file_path,
                    'line': i,
                    'type': 'todo',
                    'message': line.strip()
                })
            
            if 'print(' in line and not 'logger' in line:
                self.issues.append({
                    'file': file_path,
                    'line': i,
                    'type': 'print',
                    'message': 'Using print instead of logger'
                })
            
            if 'except:' in line:
                self.issues.append({
                    'file': file_path,
                    'line': i,
                    'type': 'bare_except',
                    'message': 'Bare except clause found'
                })
    
    def _generate_analysis_report(self) -> str:
        """Generate markdown analysis report."""
        report = """# Code Analysis Report

## Summary

"""
        
        # Metrics summary
        report += f"""### Code Metrics

- Total Lines: {self.metrics['total_lines']:,}
- Code Lines: {self.metrics['code_lines']:,}
- Comment Lines: {self.metrics['comment_lines']:,}
- Blank Lines: {self.metrics['blank_lines']:,}
- Functions: {self.metrics['functions']:,}
- Classes: {self.metrics['classes']:,}
- Average Complexity: {self.metrics['total_complexity'] / max(self.metrics['functions'], 1):.2f}

### Code Ratios

- Comment Ratio: {self.metrics['comment_lines'] / max(self.metrics['code_lines'], 1) * 100:.1f}%
- Code Density: {self.metrics['code_lines'] / max(self.metrics['total_lines'], 1) * 100:.1f}%

"""
        
        # Issues
        if self.issues:
            report += "## Issues Found\\n\\n"
            
            # Group by type
            issues_by_type = defaultdict(list)
            for issue in self.issues:
                issues_by_type[issue['type']].append(issue)
            
            for issue_type, items in issues_by_type.items():
                report += f"### {issue_type.replace('_', ' ').title()} ({len(items)})\\n\\n"
                
                for item in items[:10]:  # Show first 10
                    report += f"- `{item['file']}:{item['line']}` - {item['message']}\\n"
                
                if len(items) > 10:
                    report += f"- ... and {len(items) - 10} more\\n"
                
                report += "\\n"
        
        return report
    
    def _display_summary(self) -> None:
        """Display analysis summary."""
        self.logger.info("=" * 50)
        self.logger.info("Code Analysis Summary")
        self.logger.info("=" * 50)
        self.logger.info(f"Total Files Analyzed: {self.metrics.get('files_analyzed', 0)}")
        self.logger.info(f"Total Lines: {self.metrics['total_lines']:,}")
        self.logger.info(f"Code Quality Score: {self._calculate_quality_score()}/100")
        self.logger.info(f"Issues Found: {len(self.issues)}")
        self.logger.info("=" * 50)
    
    def _calculate_quality_score(self) -> int:
        """Calculate overall code quality score."""
        score = 100
        
        # Deduct for issues
        score -= min(len(self.issues) * 2, 30)
        
        # Deduct for lack of comments
        comment_ratio = self.metrics['comment_lines'] / max(self.metrics['code_lines'], 1)
        if comment_ratio < 0.1:
            score -= 10
        
        # Deduct for high complexity
        avg_complexity = self.metrics['total_complexity'] / max(self.metrics['functions'], 1)
        if avg_complexity > 10:
            score -= 15
        elif avg_complexity > 7:
            score -= 10
        elif avg_complexity > 5:
            score -= 5
        
        return max(score, 0)


def register():
    """Register the plugin."""
    return CodeAnalyzerPlugin()
'''
    
    @staticmethod
    def deployment_plugin() -> str:
        """Deployment automation plugin example.
        
        Returns:
            Plugin code
        """
        return '''"""Deployment plugin for Claude Code Builder."""
from claude_code_builder.cli.plugins import Plugin
from pathlib import Path
from typing import Dict, Any, Optional
import subprocess
import docker
import yaml


class DeploymentPlugin(Plugin):
    """Automate deployment of generated projects."""
    
    name = "deployment"
    version = "1.0.0"
    description = "Deploy projects to various platforms"
    
    def on_load(self, context: Dict[str, Any]) -> None:
        """Load deployment configuration."""
        config = context.get('config', {})
        
        self.deploy_on_success = config.get('deploy_on_success', False)
        self.deployment_target = config.get('target', 'docker')
        self.registry = config.get('registry', 'docker.io')
        self.namespace = config.get('namespace', 'myapp')
        
        # Platform-specific settings
        self.k8s_context = config.get('k8s_context')
        self.aws_region = config.get('aws_region', 'us-east-1')
        self.heroku_app = config.get('heroku_app')
    
    def on_build_complete(self, context: Dict[str, Any]) -> None:
        """Deploy after successful build."""
        if not self.deploy_on_success:
            self.logger.info("Deployment disabled. Set deploy_on_success=true to enable.")
            return
        
        project = context['project']
        output_dir = Path(context['output_dir'])
        
        self.logger.info(f"Deploying {project.name} to {self.deployment_target}")
        
        try:
            if self.deployment_target == 'docker':
                self._deploy_docker(output_dir, project)
            elif self.deployment_target == 'kubernetes':
                self._deploy_kubernetes(output_dir, project)
            elif self.deployment_target == 'aws':
                self._deploy_aws(output_dir, project)
            elif self.deployment_target == 'heroku':
                self._deploy_heroku(output_dir, project)
            else:
                self.logger.error(f"Unknown deployment target: {self.deployment_target}")
                
        except Exception as e:
            self.logger.error(f"Deployment failed: {e}")
            # Don't fail the build for deployment errors
    
    def _deploy_docker(self, output_dir: Path, project: Any) -> None:
        """Deploy using Docker."""
        dockerfile = output_dir / 'Dockerfile'
        
        if not dockerfile.exists():
            self._generate_dockerfile(output_dir, project)
        
        # Build image
        image_name = f"{self.registry}/{self.namespace}/{project.name}:latest"
        
        self.logger.info(f"Building Docker image: {image_name}")
        
        client = docker.from_env()
        image, logs = client.images.build(
            path=str(output_dir),
            tag=image_name,
            rm=True
        )
        
        for log in logs:
            if 'stream' in log:
                self.logger.debug(log['stream'].strip())
        
        # Push to registry
        if self.registry != 'local':
            self.logger.info(f"Pushing image to {self.registry}")
            client.images.push(image_name)
        
        # Run locally for testing
        self.logger.info("Starting container locally")
        container = client.containers.run(
            image_name,
            detach=True,
            ports={'8000/tcp': 8000},
            name=f"{project.name}-dev"
        )
        
        self.logger.info(f"Container started: {container.id[:12]}")
        self.logger.info("Access at: http://localhost:8000")
    
    def _deploy_kubernetes(self, output_dir: Path, project: Any) -> None:
        """Deploy to Kubernetes."""
        k8s_dir = output_dir / 'k8s'
        
        if not k8s_dir.exists():
            self._generate_k8s_manifests(output_dir, project)
        
        # Apply manifests
        self.logger.info("Applying Kubernetes manifests")
        
        for manifest in k8s_dir.glob('*.yaml'):
            cmd = ['kubectl', 'apply', '-f', str(manifest)]
            
            if self.k8s_context:
                cmd.extend(['--context', self.k8s_context])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"Applied: {manifest.name}")
            else:
                self.logger.error(f"Failed to apply {manifest.name}: {result.stderr}")
    
    def _deploy_aws(self, output_dir: Path, project: Any) -> None:
        """Deploy to AWS."""
        # This is a simplified example - real deployment would be more complex
        
        # Check for SAM template
        sam_template = output_dir / 'template.yaml'
        if sam_template.exists():
            self._deploy_sam(output_dir, project)
        else:
            self._deploy_ecs(output_dir, project)
    
    def _deploy_heroku(self, output_dir: Path, project: Any) -> None:
        """Deploy to Heroku."""
        if not self.heroku_app:
            self.logger.error("Heroku app name not configured")
            return
        
        # Ensure git repo
        if not (output_dir / '.git').exists():
            subprocess.run(['git', 'init'], cwd=output_dir)
            subprocess.run(['git', 'add', '.'], cwd=output_dir)
            subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=output_dir)
        
        # Add Heroku remote
        subprocess.run([
            'heroku', 'git:remote', '-a', self.heroku_app
        ], cwd=output_dir)
        
        # Deploy
        self.logger.info(f"Deploying to Heroku app: {self.heroku_app}")
        result = subprocess.run(
            ['git', 'push', 'heroku', 'main'],
            cwd=output_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            self.logger.info("Deployment successful!")
            self.logger.info(f"App URL: https://{self.heroku_app}.herokuapp.com")
        else:
            self.logger.error(f"Deployment failed: {result.stderr}")
    
    def _generate_dockerfile(self, output_dir: Path, project: Any) -> None:
        """Generate Dockerfile if not present."""
        dockerfile_content = """FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
        
        (output_dir / 'Dockerfile').write_text(dockerfile_content)
        self.logger.info("Generated Dockerfile")
    
    def _generate_k8s_manifests(self, output_dir: Path, project: Any) -> None:
        """Generate Kubernetes manifests."""
        k8s_dir = output_dir / 'k8s'
        k8s_dir.mkdir(exist_ok=True)
        
        # Deployment
        deployment = {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': project.name
            },
            'spec': {
                'replicas': 2,
                'selector': {
                    'matchLabels': {
                        'app': project.name
                    }
                },
                'template': {
                    'metadata': {
                        'labels': {
                            'app': project.name
                        }
                    },
                    'spec': {
                        'containers': [{
                            'name': project.name,
                            'image': f"{self.registry}/{self.namespace}/{project.name}:latest",
                            'ports': [{
                                'containerPort': 8000
                            }]
                        }]
                    }
                }
            }
        }
        
        with open(k8s_dir / 'deployment.yaml', 'w') as f:
            yaml.dump(deployment, f)
        
        # Service
        service = {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': project.name
            },
            'spec': {
                'selector': {
                    'app': project.name
                },
                'ports': [{
                    'protocol': 'TCP',
                    'port': 80,
                    'targetPort': 8000
                }],
                'type': 'LoadBalancer'
            }
        }
        
        with open(k8s_dir / 'service.yaml', 'w') as f:
            yaml.dump(service, f)
        
        self.logger.info("Generated Kubernetes manifests")


def register():
    """Register the plugin."""
    return DeploymentPlugin()
'''
    
    @staticmethod
    def test_runner_plugin() -> str:
        """Test runner plugin example.
        
        Returns:
            Plugin code
        """
        return '''"""Test runner plugin for Claude Code Builder."""
from claude_code_builder.cli.plugins import Plugin
from pathlib import Path
from typing import Dict, Any, List
import subprocess
import json
import time


class TestRunnerPlugin(Plugin):
    """Automatically run tests after build completion."""
    
    name = "test_runner"
    version = "1.0.0"
    description = "Run tests and generate coverage reports"
    
    def on_load(self, context: Dict[str, Any]) -> None:
        """Load test configuration."""
        config = context.get('config', {})
        
        self.run_tests = config.get('run_tests', True)
        self.coverage_threshold = config.get('coverage_threshold', 80)
        self.test_frameworks = {
            'python': config.get('python_framework', 'pytest'),
            'javascript': config.get('js_framework', 'jest'),
            'go': config.get('go_framework', 'go test')
        }
        self.fail_on_test_failure = config.get('fail_on_test_failure', False)
    
    def on_build_complete(self, context: Dict[str, Any]) -> None:
        """Run tests after successful build."""
        if not self.run_tests:
            return
        
        output_dir = Path(context['output_dir'])
        project = context['project']
        
        self.logger.info("Running tests...")
        
        # Detect project language
        language = self._detect_language(output_dir)
        
        if language == 'python':
            self._run_python_tests(output_dir)
        elif language == 'javascript':
            self._run_javascript_tests(output_dir)
        elif language == 'go':
            self._run_go_tests(output_dir)
        else:
            self.logger.warning(f"No test runner configured for {language}")
    
    def _detect_language(self, output_dir: Path) -> str:
        """Detect project language."""
        if (output_dir / 'requirements.txt').exists() or (output_dir / 'setup.py').exists():
            return 'python'
        elif (output_dir / 'package.json').exists():
            return 'javascript'
        elif (output_dir / 'go.mod').exists():
            return 'go'
        else:
            return 'unknown'
    
    def _run_python_tests(self, output_dir: Path) -> None:
        """Run Python tests with pytest."""
        test_dir = output_dir / 'tests'
        if not test_dir.exists():
            self.logger.warning("No tests directory found")
            return
        
        # Install test dependencies
        self.logger.info("Installing test dependencies...")
        subprocess.run(
            ['pip', 'install', 'pytest', 'pytest-cov', 'pytest-html'],
            cwd=output_dir,
            capture_output=True
        )
        
        # Run tests with coverage
        start_time = time.time()
        
        cmd = [
            'pytest',
            str(test_dir),
            '--cov=' + str(output_dir.name),
            '--cov-report=html',
            '--cov-report=json',
            '--cov-report=term',
            '--html=test-report.html',
            '--self-contained-html',
            '-v'
        ]
        
        result = subprocess.run(
            cmd,
            cwd=output_dir,
            capture_output=True,
            text=True
        )
        
        duration = time.time() - start_time
        
        # Parse results
        self._parse_pytest_results(output_dir, result, duration)
    
    def _run_javascript_tests(self, output_dir: Path) -> None:
        """Run JavaScript tests with Jest."""
        # Check if jest is configured
        package_json = output_dir / 'package.json'
        if not package_json.exists():
            return
        
        # Install dependencies
        self.logger.info("Installing dependencies...")
        subprocess.run(['npm', 'install'], cwd=output_dir, capture_output=True)
        
        # Run tests
        start_time = time.time()
        
        cmd = ['npm', 'test', '--', '--coverage', '--json', '--outputFile=test-results.json']
        
        result = subprocess.run(
            cmd,
            cwd=output_dir,
            capture_output=True,
            text=True
        )
        
        duration = time.time() - start_time
        
        # Parse results
        self._parse_jest_results(output_dir, result, duration)
    
    def _run_go_tests(self, output_dir: Path) -> None:
        """Run Go tests."""
        start_time = time.time()
        
        # Run tests with coverage
        cmd = ['go', 'test', '-v', '-cover', '-coverprofile=coverage.out', './...']
        
        result = subprocess.run(
            cmd,
            cwd=output_dir,
            capture_output=True,
            text=True
        )
        
        duration = time.time() - start_time
        
        # Generate coverage report
        if result.returncode == 0:
            subprocess.run(
                ['go', 'tool', 'cover', '-html=coverage.out', '-o', 'coverage.html'],
                cwd=output_dir
            )
        
        self._display_test_summary('Go', result.returncode == 0, duration)
    
    def _parse_pytest_results(self, output_dir: Path, result: Any, duration: float) -> None:
        """Parse pytest results."""
        # Extract test summary from output
        output_lines = result.stdout.split('\\n')
        
        passed = failed = skipped = 0
        coverage = 0.0
        
        for line in output_lines:
            if 'passed' in line and 'failed' in line:
                # Parse summary line
                parts = line.split()
                for i, part in enumerate(parts):
                    if 'passed' in part:
                        passed = int(parts[i-1])
                    elif 'failed' in part:
                        failed = int(parts[i-1])
                    elif 'skipped' in part:
                        skipped = int(parts[i-1])
            elif 'TOTAL' in line and '%' in line:
                # Parse coverage
                parts = line.split()
                for part in parts:
                    if '%' in part:
                        coverage = float(part.replace('%', ''))
                        break
        
        # Load detailed coverage report
        coverage_file = output_dir / 'coverage.json'
        if coverage_file.exists():
            with open(coverage_file) as f:
                coverage_data = json.load(f)
                coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
        
        # Display results
        self._display_test_summary(
            'Python',
            result.returncode == 0,
            duration,
            passed=passed,
            failed=failed,
            skipped=skipped,
            coverage=coverage
        )
        
        # Check coverage threshold
        if coverage < self.coverage_threshold:
            self.logger.warning(
                f"Coverage {coverage:.1f}% is below threshold {self.coverage_threshold}%"
            )
    
    def _display_test_summary(
        self,
        language: str,
        success: bool,
        duration: float,
        **kwargs
    ) -> None:
        """Display test summary."""
        self.logger.info("=" * 60)
        self.logger.info(f"{language} Test Results")
        self.logger.info("=" * 60)
        
        if success:
            self.logger.info("✅ All tests passed!")
        else:
            self.logger.error("❌ Some tests failed!")
        
        self.logger.info(f"Duration: {duration:.2f}s")
        
        if 'passed' in kwargs:
            self.logger.info(f"Passed: {kwargs['passed']}")
        if 'failed' in kwargs:
            self.logger.info(f"Failed: {kwargs['failed']}")
        if 'skipped' in kwargs:
            self.logger.info(f"Skipped: {kwargs['skipped']}")
        if 'coverage' in kwargs:
            self.logger.info(f"Coverage: {kwargs['coverage']:.1f}%")
        
        self.logger.info("=" * 60)


def register():
    """Register the plugin."""
    return TestRunnerPlugin()
'''
    
    @staticmethod
    def documentation_plugin() -> str:
        """Documentation generator plugin example.
        
        Returns:
            Plugin code
        """
        return '''"""Documentation generator plugin for Claude Code Builder."""
from claude_code_builder.cli.plugins import Plugin
from pathlib import Path
from typing import Dict, Any, List, Optional
import subprocess
import ast
import re


class DocumentationPlugin(Plugin):
    """Generate comprehensive documentation for projects."""
    
    name = "documentation"
    version = "1.0.0"
    description = "Generates API docs, diagrams, and documentation sites"
    
    def on_load(self, context: Dict[str, Any]) -> None:
        """Load documentation settings."""
        config = context.get('config', {})
        
        self.generate_api_docs = config.get('api_docs', True)
        self.generate_diagrams = config.get('diagrams', True)
        self.generate_site = config.get('site', False)
        self.doc_format = config.get('format', 'markdown')
        self.theme = config.get('theme', 'mkdocs-material')
    
    def on_build_complete(self, context: Dict[str, Any]) -> None:
        """Generate documentation after build."""
        output_dir = Path(context['output_dir'])
        project = context['project']
        
        self.logger.info("Generating documentation...")
        
        # Create docs directory
        docs_dir = output_dir / 'docs'
        docs_dir.mkdir(exist_ok=True)
        
        # Generate different types of documentation
        if self.generate_api_docs:
            self._generate_api_documentation(output_dir, docs_dir)
        
        if self.generate_diagrams:
            self._generate_diagrams(output_dir, docs_dir)
        
        if self.generate_site:
            self._generate_documentation_site(output_dir, docs_dir, project)
        
        # Generate main README if not exists
        if not (output_dir / 'README.md').exists():
            self._generate_readme(output_dir, project)
    
    def _generate_api_documentation(self, output_dir: Path, docs_dir: Path) -> None:
        """Generate API documentation."""
        api_dir = docs_dir / 'api'
        api_dir.mkdir(exist_ok=True)
        
        # Find Python files
        python_files = list(output_dir.glob('**/*.py'))
        
        for py_file in python_files:
            if 'test' not in str(py_file) and '__pycache__' not in str(py_file):
                self._document_python_module(py_file, api_dir)
        
        # Generate API index
        self._generate_api_index(api_dir)
    
    def _document_python_module(self, py_file: Path, api_dir: Path) -> None:
        """Document a Python module."""
        try:
            content = py_file.read_text()
            tree = ast.parse(content)
            
            module_doc = ast.get_docstring(tree) or "No module documentation."
            
            # Prepare documentation
            doc_content = f"# {py_file.stem}\\n\\n"
            doc_content += f"{module_doc}\\n\\n"
            
            # Document classes
            classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
            if classes:
                doc_content += "## Classes\\n\\n"
                for cls in classes:
                    doc_content += self._document_class(cls)
            
            # Document functions
            functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
            if functions:
                doc_content += "## Functions\\n\\n"
                for func in functions:
                    doc_content += self._document_function(func)
            
            # Save documentation
            doc_file = api_dir / f"{py_file.stem}.md"
            doc_file.write_text(doc_content)
            
        except Exception as e:
            self.logger.error(f"Error documenting {py_file}: {e}")
    
    def _document_class(self, node: ast.ClassDef) -> str:
        """Document a class."""
        doc = f"### {node.name}\\n\\n"
        
        docstring = ast.get_docstring(node)
        if docstring:
            doc += f"{docstring}\\n\\n"
        
        # Document methods
        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        if methods:
            doc += "**Methods:**\\n\\n"
            for method in methods:
                if not method.name.startswith('_') or method.name == '__init__':
                    doc += self._document_function(method, is_method=True)
        
        return doc
    
    def _document_function(self, node: ast.FunctionDef, is_method: bool = False) -> str:
        """Document a function."""
        # Build signature
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        
        signature = f"{node.name}({', '.join(args)})"
        
        if is_method:
            doc = f"- `{signature}`"
        else:
            doc = f"### {signature}"
        
        doc += "\\n\\n"
        
        docstring = ast.get_docstring(node)
        if docstring:
            doc += f"  {docstring}\\n\\n"
        
        return doc
    
    def _generate_diagrams(self, output_dir: Path, docs_dir: Path) -> None:
        """Generate architecture diagrams."""
        diagrams_dir = docs_dir / 'diagrams'
        diagrams_dir.mkdir(exist_ok=True)
        
        # Generate class diagram using mermaid
        self._generate_class_diagram(output_dir, diagrams_dir)
        
        # Generate architecture diagram
        self._generate_architecture_diagram(output_dir, diagrams_dir)
    
    def _generate_class_diagram(self, output_dir: Path, diagrams_dir: Path) -> None:
        """Generate class diagram."""
        mermaid_content = "classDiagram\\n"
        
        # Find Python files and extract classes
        for py_file in output_dir.glob('**/*.py'):
            if 'test' not in str(py_file) and '__pycache__' not in str(py_file):
                try:
                    content = py_file.read_text()
                    tree = ast.parse(content)
                    
                    for node in tree.body:
                        if isinstance(node, ast.ClassDef):
                            mermaid_content += f"    class {node.name} {{\\n"
                            
                            # Add methods
                            for item in node.body:
                                if isinstance(item, ast.FunctionDef):
                                    mermaid_content += f"        +{item.name}()\\n"
                            
                            mermaid_content += "    }\\n"
                            
                except Exception:
                    pass
        
        # Save diagram
        diagram_file = diagrams_dir / 'class_diagram.mmd'
        diagram_file.write_text(mermaid_content)
    
    def _generate_architecture_diagram(self, output_dir: Path, diagrams_dir: Path) -> None:
        """Generate architecture diagram."""
        # This is a simple example - real implementation would analyze imports
        mermaid_content = """graph TB
    Client[Client] --> API[API Layer]
    API --> Service[Service Layer]
    Service --> Repository[Repository Layer]
    Repository --> Database[(Database)]
    
    API --> Auth[Authentication]
    Auth --> JWT[JWT Tokens]
    
    Service --> Cache[Cache Layer]
    Cache --> Redis[(Redis)]
"""
        
        diagram_file = diagrams_dir / 'architecture.mmd'
        diagram_file.write_text(mermaid_content)
    
    def _generate_documentation_site(
        self,
        output_dir: Path,
        docs_dir: Path,
        project: Any
    ) -> None:
        """Generate documentation website."""
        # Create MkDocs configuration
        mkdocs_config = f"""site_name: {project.name} Documentation
site_description: Documentation for {project.name}
site_author: Generated by Claude Code Builder

theme:
  name: material
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - search.highlight
    - search.share

nav:
  - Home: index.md
  - Getting Started: getting-started.md
  - API Reference: api/
  - Architecture: architecture.md
  - Contributing: contributing.md

plugins:
  - search
  - mermaid2

markdown_extensions:
  - admonition
  - codehilite
  - meta
  - toc:
      permalink: true
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
"""
        
        mkdocs_file = output_dir / 'mkdocs.yml'
        mkdocs_file.write_text(mkdocs_config)
        
        # Create index page
        index_content = f"""# {project.name}

Welcome to the {project.name} documentation!

## Overview

{project.description}

## Quick Start

```bash
# Installation
pip install -r requirements.txt

# Run the application
python main.py
```

## Features

"""
        
        for phase in project.phases:
            index_content += f"- {phase.name}\\n"
        
        (docs_dir / 'index.md').write_text(index_content)
        
        # Generate getting started guide
        self._generate_getting_started(docs_dir, project)
        
        self.logger.info("Documentation site generated. Run 'mkdocs serve' to preview.")
    
    def _generate_getting_started(self, docs_dir: Path, project: Any) -> None:
        """Generate getting started guide."""
        content = f"""# Getting Started with {project.name}

## Prerequisites

- Python 3.8 or higher
- pip package manager

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd {project.name}
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Create a `.env` file with your configuration:

```env
# Example configuration
DEBUG=True
DATABASE_URL=sqlite:///app.db
SECRET_KEY=your-secret-key
```

## Running the Application

```bash
python main.py
```

## Next Steps

- Read the [API Reference](api/)
- Learn about the [Architecture](architecture.md)
- [Contribute](contributing.md) to the project
"""
        
        (docs_dir / 'getting-started.md').write_text(content)
    
    def _generate_readme(self, output_dir: Path, project: Any) -> None:
        """Generate README file."""
        readme_content = f"""# {project.name}

{project.description}

## Features

"""
        
        for phase in project.phases:
            readme_content += f"- ✅ {phase.name}\\n"
        
        readme_content += """
## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Documentation

See the [docs](docs/) directory for detailed documentation.

## License

This project is licensed under the MIT License.

---

Generated with ❤️ by Claude Code Builder
"""
        
        (output_dir / 'README.md').write_text(readme_content)
    
    def _generate_api_index(self, api_dir: Path) -> None:
        """Generate API documentation index."""
        index_content = "# API Reference\\n\\n"
        index_content += "## Modules\\n\\n"
        
        for md_file in sorted(api_dir.glob('*.md')):
            if md_file.name != 'index.md':
                module_name = md_file.stem
                index_content += f"- [{module_name}]({md_file.name})\\n"
        
        (api_dir / 'index.md').write_text(index_content)


def register():
    """Register the plugin."""
    return DocumentationPlugin()
'''
    
    @staticmethod
    def metrics_collector_plugin() -> str:
        """Metrics collection plugin example.
        
        Returns:
            Plugin code
        """
        return '''"""Metrics collector plugin for Claude Code Builder."""
from claude_code_builder.cli.plugins import Plugin
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import json
import time
from collections import defaultdict


class MetricsCollectorPlugin(Plugin):
    """Collect and analyze build metrics."""
    
    name = "metrics_collector"
    version = "1.0.0"
    description = "Collects detailed metrics about builds for analysis"
    
    def __init__(self):
        """Initialize metrics collector."""
        super().__init__()
        self.current_build = {}
        self.phase_metrics = defaultdict(dict)
        self.file_metrics = defaultdict(int)
    
    def on_pre_build(self, context: Dict[str, Any]) -> None:
        """Start collecting build metrics."""
        project = context['project']
        
        self.current_build = {
            'id': self._generate_build_id(),
            'project_name': project.name,
            'start_time': time.time(),
            'timestamp': datetime.now().isoformat(),
            'phases': {},
            'files': {},
            'errors': [],
            'system_info': self._get_system_info()
        }
        
        self.logger.info(f"Starting metrics collection for build {self.current_build['id']}")
    
    def on_pre_phase(self, context: Dict[str, Any]) -> None:
        """Start collecting phase metrics."""
        phase = context['phase']
        phase_key = f"{context['phase_number']}_{phase.name}"
        
        self.phase_metrics[phase_key] = {
            'name': phase.name,
            'number': context['phase_number'],
            'start_time': time.time(),
            'memory_start': self._get_memory_usage()
        }
    
    def on_post_phase(self, context: Dict[str, Any]) -> None:
        """Collect phase completion metrics."""
        phase = context['phase']
        phase_key = f"{context['phase_number']}_{phase.name}"
        
        if phase_key in self.phase_metrics:
            metrics = self.phase_metrics[phase_key]
            metrics['end_time'] = time.time()
            metrics['duration'] = metrics['end_time'] - metrics['start_time']
            metrics['memory_end'] = self._get_memory_usage()
            metrics['memory_delta'] = metrics['memory_end'] - metrics['memory_start']
            metrics['files_created'] = len(context.get('created_files', []))
            metrics['tokens_used'] = context.get('tokens_used', 0)
            
            # Store in current build
            self.current_build['phases'][phase_key] = metrics
            
            # Analyze created files
            for file_path in context.get('created_files', []):
                self._analyze_file(file_path)
    
    def on_build_complete(self, context: Dict[str, Any]) -> None:
        """Finalize and save build metrics."""
        self.current_build['end_time'] = time.time()
        self.current_build['total_duration'] = self.current_build['end_time'] - self.current_build['start_time']
        self.current_build['status'] = 'completed'
        self.current_build['output_dir'] = str(context['output_dir'])
        
        # Calculate aggregates
        self._calculate_aggregates()
        
        # Save metrics
        self._save_metrics(context['output_dir'])
        
        # Display summary
        self._display_metrics_summary()
    
    def on_build_failed(self, context: Dict[str, Any]) -> None:
        """Handle build failure metrics."""
        self.current_build['end_time'] = time.time()
        self.current_build['total_duration'] = self.current_build['end_time'] - self.current_build['start_time']
        self.current_build['status'] = 'failed'
        self.current_build['error'] = str(context.get('error', 'Unknown error'))
        self.current_build['failed_phase'] = context.get('failed_phase', 'Unknown')
        
        # Save partial metrics
        if 'output_dir' in context:
            self._save_metrics(context['output_dir'])
    
    def _analyze_file(self, file_path: str) -> None:
        """Analyze created file."""
        path = Path(file_path)
        
        if path.exists():
            stat = path.stat()
            ext = path.suffix.lower()
            
            file_info = {
                'path': str(path),
                'size': stat.st_size,
                'extension': ext,
                'lines': 0
            }
            
            # Count lines for text files
            if ext in ['.py', '.js', '.ts', '.java', '.go', '.rs', '.md', '.txt']:
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        file_info['lines'] = sum(1 for _ in f)
                except Exception:
                    pass
            
            self.current_build['files'][str(path)] = file_info
            self.file_metrics[ext] += 1
    
    def _calculate_aggregates(self) -> None:
        """Calculate aggregate metrics."""
        phases = self.current_build['phases'].values()
        
        self.current_build['aggregates'] = {
            'total_phases': len(phases),
            'total_phase_duration': sum(p['duration'] for p in phases),
            'average_phase_duration': sum(p['duration'] for p in phases) / len(phases) if phases else 0,
            'total_files_created': sum(p['files_created'] for p in phases),
            'total_tokens_used': sum(p.get('tokens_used', 0) for p in phases),
            'total_memory_delta': sum(p.get('memory_delta', 0) for p in phases),
            'file_types': dict(self.file_metrics),
            'total_file_size': sum(f['size'] for f in self.current_build['files'].values()),
            'total_lines_of_code': sum(f.get('lines', 0) for f in self.current_build['files'].values())
        }
    
    def _save_metrics(self, output_dir: Path) -> None:
        """Save metrics to file."""
        metrics_dir = output_dir / '.build-metrics'
        metrics_dir.mkdir(exist_ok=True)
        
        # Save current build metrics
        metrics_file = metrics_dir / f"build_{self.current_build['id']}.json"
        with open(metrics_file, 'w') as f:
            json.dump(self.current_build, f, indent=2)
        
        # Update aggregate metrics
        self._update_aggregate_metrics(metrics_dir)
        
        self.logger.info(f"Metrics saved to {metrics_file}")
    
    def _update_aggregate_metrics(self, metrics_dir: Path) -> None:
        """Update aggregate metrics file."""
        aggregate_file = metrics_dir / 'aggregate_metrics.json'
        
        if aggregate_file.exists():
            with open(aggregate_file) as f:
                aggregate = json.load(f)
        else:
            aggregate = {
                'total_builds': 0,
                'successful_builds': 0,
                'failed_builds': 0,
                'total_duration': 0,
                'total_files_created': 0,
                'builds': []
            }
        
        # Update aggregates
        aggregate['total_builds'] += 1
        if self.current_build['status'] == 'completed':
            aggregate['successful_builds'] += 1
        else:
            aggregate['failed_builds'] += 1
        
        aggregate['total_duration'] += self.current_build['total_duration']
        aggregate['total_files_created'] += self.current_build.get('aggregates', {}).get('total_files_created', 0)
        
        # Add build summary
        aggregate['builds'].append({
            'id': self.current_build['id'],
            'timestamp': self.current_build['timestamp'],
            'project_name': self.current_build['project_name'],
            'status': self.current_build['status'],
            'duration': self.current_build['total_duration'],
            'files_created': self.current_build.get('aggregates', {}).get('total_files_created', 0)
        })
        
        # Keep only last 100 builds
        aggregate['builds'] = aggregate['builds'][-100:]
        
        with open(aggregate_file, 'w') as f:
            json.dump(aggregate, f, indent=2)
    
    def _display_metrics_summary(self) -> None:
        """Display metrics summary."""
        agg = self.current_build.get('aggregates', {})
        
        self.logger.info("=" * 60)
        self.logger.info("Build Metrics Summary")
        self.logger.info("=" * 60)
        self.logger.info(f"Build ID: {self.current_build['id']}")
        self.logger.info(f"Total Duration: {self.current_build['total_duration']:.2f}s")
        self.logger.info(f"Phases Completed: {agg.get('total_phases', 0)}")
        self.logger.info(f"Files Created: {agg.get('total_files_created', 0)}")
        self.logger.info(f"Total Lines of Code: {agg.get('total_lines_of_code', 0):,}")
        self.logger.info(f"Total File Size: {agg.get('total_file_size', 0) / 1024:.2f} KB")
        
        if agg.get('file_types'):
            self.logger.info("\\nFile Types Created:")
            for ext, count in sorted(agg['file_types'].items()):
                self.logger.info(f"  {ext}: {count}")
        
        self.logger.info("=" * 60)
    
    def _generate_build_id(self) -> str:
        """Generate unique build ID."""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        import platform
        import psutil
        
        return {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'disk_free': psutil.disk_usage('/').free
        }
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024


def register():
    """Register the plugin."""
    return MetricsCollectorPlugin()
'''
    
    @staticmethod
    def security_scanner_plugin() -> str:
        """Security scanning plugin example.
        
        Returns:
            Plugin code
        """
        return '''"""Security scanner plugin for Claude Code Builder."""
from claude_code_builder.cli.plugins import Plugin
from pathlib import Path
from typing import Dict, Any, List, Tuple
import re
import subprocess
import json
from datetime import datetime


class SecurityScannerPlugin(Plugin):
    """Scan generated code for security vulnerabilities."""
    
    name = "security_scanner"
    version = "1.0.0"
    description = "Scans code for security vulnerabilities and best practices"
    
    def __init__(self):
        """Initialize scanner."""
        super().__init__()
        self.vulnerabilities = []
        self.security_score = 100
    
    def on_load(self, context: Dict[str, Any]) -> None:
        """Load security configuration."""
        config = context.get('config', {})
        
        self.scan_enabled = config.get('enabled', True)
        self.fail_on_high = config.get('fail_on_high_severity', False)
        self.scan_dependencies = config.get('scan_dependencies', True)
        self.scan_secrets = config.get('scan_secrets', True)
        self.custom_rules = config.get('custom_rules', [])
    
    def on_build_complete(self, context: Dict[str, Any]) -> None:
        """Run security scans after build."""
        if not self.scan_enabled:
            return
        
        output_dir = Path(context['output_dir'])
        
        self.logger.info("Running security scans...")
        
        # Run various security checks
        self._scan_for_secrets(output_dir)
        self._scan_for_vulnerabilities(output_dir)
        self._scan_dependencies(output_dir)
        self._check_security_headers(output_dir)
        self._scan_for_injection_vulnerabilities(output_dir)
        
        # Generate report
        self._generate_security_report(output_dir)
        
        # Display summary
        self._display_security_summary()
        
        # Fail build if critical issues found
        if self.fail_on_high and self._has_high_severity_issues():
            raise Exception("High severity security issues found!")
    
    def _scan_for_secrets(self, output_dir: Path) -> None:
        """Scan for hardcoded secrets and sensitive data."""
        secret_patterns = [
            (r'api[_-]?key\\s*=\\s*["\']([^"\']+)["\']', 'API Key'),
            (r'secret[_-]?key\\s*=\\s*["\']([^"\']+)["\']', 'Secret Key'),
            (r'password\\s*=\\s*["\']([^"\']+)["\']', 'Hardcoded Password'),
            (r'aws_access_key_id\\s*=\\s*["\']([^"\']+)["\']', 'AWS Access Key'),
            (r'aws_secret_access_key\\s*=\\s*["\']([^"\']+)["\']', 'AWS Secret Key'),
            (r'mongodb://[^\\s]+', 'MongoDB Connection String'),
            (r'postgres://[^\\s]+', 'PostgreSQL Connection String'),
            (r'mysql://[^\\s]+', 'MySQL Connection String'),
            (r'private[_-]?key\\s*=\\s*["\']([^"\']+)["\']', 'Private Key'),
            (r'token\\s*=\\s*["\']([^"\']+)["\']', 'Access Token'),
            (r'[A-Za-z0-9+/]{40,}={0,2}', 'Base64 Encoded Secret')
        ]
        
        for file_path in output_dir.glob('**/*'):
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.env', '.config', '.json', '.yaml']:
                try:
                    content = file_path.read_text()
                    
                    for pattern, secret_type in secret_patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            # Skip if it's a placeholder
                            value = match.group(0)
                            if not any(placeholder in value.lower() for placeholder in ['example', 'placeholder', 'your-', '<']):
                                self._add_vulnerability(
                                    'secret',
                                    'high',
                                    f'{secret_type} found',
                                    str(file_path),
                                    match.start()
                                )
                
                except Exception as e:
                    self.logger.debug(f"Error scanning {file_path}: {e}")
    
    def _scan_for_vulnerabilities(self, output_dir: Path) -> None:
        """Scan for common security vulnerabilities."""
        vuln_patterns = {
            'python': [
                (r'eval\\s*\\(', 'Code Injection', 'Use of eval()'),
                (r'exec\\s*\\(', 'Code Injection', 'Use of exec()'),
                (r'pickle\\.loads', 'Deserialization', 'Unsafe pickle deserialization'),
                (r'subprocess\\.(call|run|Popen)\\s*\\([^,)]*shell\\s*=\\s*True', 'Command Injection', 'Shell=True in subprocess'),
                (r'os\\.system\\s*\\(', 'Command Injection', 'Use of os.system()'),
                (r'\\.execute\\s*\\(.*%.*%', 'SQL Injection', 'String formatting in SQL'),
                (r'verify\\s*=\\s*False', 'SSL Verification', 'SSL verification disabled'),
                (r'debug\\s*=\\s*True', 'Debug Mode', 'Debug mode enabled')
            ],
            'javascript': [
                (r'eval\\s*\\(', 'Code Injection', 'Use of eval()'),
                (r'innerHTML\\s*=', 'XSS', 'Direct innerHTML assignment'),
                (r'document\\.write\\s*\\(', 'XSS', 'Use of document.write()'),
                (r'dangerouslySetInnerHTML', 'XSS', 'React dangerouslySetInnerHTML'),
                (r'child_process\\.exec\\s*\\(', 'Command Injection', 'Use of child_process.exec()'),
                (r'new\\s+Function\\s*\\(', 'Code Injection', 'Dynamic function creation')
            ]
        }
        
        for file_path in output_dir.glob('**/*'):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                patterns = []
                
                if ext == '.py':
                    patterns = vuln_patterns.get('python', [])
                elif ext in ['.js', '.jsx', '.ts', '.tsx']:
                    patterns = vuln_patterns.get('javascript', [])
                
                if patterns:
                    self._scan_file_for_patterns(file_path, patterns)
    
    def _scan_file_for_patterns(self, file_path: Path, patterns: List[Tuple]) -> None:
        """Scan a file for vulnerability patterns."""
        try:
            content = file_path.read_text()
            
            for pattern, vuln_type, description in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    self._add_vulnerability(
                        vuln_type.lower().replace(' ', '_'),
                        'medium',
                        description,
                        str(file_path),
                        match.start()
                    )
                    
        except Exception as e:
            self.logger.debug(f"Error scanning {file_path}: {e}")
    
    def _scan_dependencies(self, output_dir: Path) -> None:
        """Scan dependencies for known vulnerabilities."""
        if not self.scan_dependencies:
            return
        
        # Check Python dependencies
        requirements_file = output_dir / 'requirements.txt'
        if requirements_file.exists():
            self._scan_python_dependencies(requirements_file)
        
        # Check JavaScript dependencies
        package_json = output_dir / 'package.json'
        if package_json.exists():
            self._scan_npm_dependencies(output_dir)
    
    def _scan_python_dependencies(self, requirements_file: Path) -> None:
        """Scan Python dependencies using safety."""
        try:
            # Try to use safety if installed
            result = subprocess.run(
                ['safety', 'check', '-r', str(requirements_file), '--json'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                vulnerabilities = json.loads(result.stdout)
                for vuln in vulnerabilities:
                    self._add_vulnerability(
                        'dependency',
                        'high',
                        f"{vuln['package']}: {vuln['vulnerability']}",
                        'requirements.txt'
                    )
        except (subprocess.SubprocessError, FileNotFoundError):
            # Safety not installed, do basic checks
            self._basic_dependency_check(requirements_file)
    
    def _scan_npm_dependencies(self, output_dir: Path) -> None:
        """Scan npm dependencies using npm audit."""
        try:
            result = subprocess.run(
                ['npm', 'audit', '--json'],
                cwd=output_dir,
                capture_output=True,
                text=True
            )
            
            if result.stdout:
                audit_data = json.loads(result.stdout)
                if 'vulnerabilities' in audit_data:
                    for severity, count in audit_data['vulnerabilities'].items():
                        if count > 0:
                            self._add_vulnerability(
                                'dependency',
                                severity,
                                f'{count} {severity} vulnerabilities in npm dependencies',
                                'package.json'
                            )
        except (subprocess.SubprocessError, FileNotFoundError):
            self.logger.debug("npm audit not available")
    
    def _check_security_headers(self, output_dir: Path) -> None:
        """Check for security headers in web applications."""
        # Look for web framework files
        for file_path in output_dir.glob('**/*.py'):
            try:
                content = file_path.read_text()
                
                # Check for Flask/FastAPI security headers
                if 'flask' in content.lower() or 'fastapi' in content.lower():
                    security_headers = [
                        'X-Frame-Options',
                        'X-Content-Type-Options',
                        'X-XSS-Protection',
                        'Strict-Transport-Security',
                        'Content-Security-Policy'
                    ]
                    
                    for header in security_headers:
                        if header not in content:
                            self._add_vulnerability(
                                'missing_header',
                                'low',
                                f'Missing security header: {header}',
                                str(file_path)
                            )
                            
            except Exception:
                pass
    
    def _scan_for_injection_vulnerabilities(self, output_dir: Path) -> None:
        """Scan for injection vulnerabilities."""
        sql_patterns = [
            r'f".*SELECT.*{.*}.*FROM',  # f-string SQL
            r'".*SELECT.*" \\+ .*',      # String concatenation SQL
            r'%s.*SELECT.*FROM',         # String formatting SQL
        ]
        
        for file_path in output_dir.glob('**/*.py'):
            try:
                content = file_path.read_text()
                
                for pattern in sql_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        self._add_vulnerability(
                            'sql_injection',
                            'high',
                            'Potential SQL injection vulnerability',
                            str(file_path)
                        )
                        break
                        
            except Exception:
                pass
    
    def _add_vulnerability(
        self,
        vuln_type: str,
        severity: str,
        description: str,
        file_path: str,
        line_number: int = 0
    ) -> None:
        """Add a vulnerability to the list."""
        self.vulnerabilities.append({
            'type': vuln_type,
            'severity': severity,
            'description': description,
            'file': file_path,
            'line': line_number,
            'timestamp': datetime.now().isoformat()
        })
        
        # Deduct from security score
        severity_scores = {'low': 5, 'medium': 10, 'high': 20, 'critical': 30}
        self.security_score -= severity_scores.get(severity, 5)
        self.security_score = max(0, self.security_score)
    
    def _basic_dependency_check(self, requirements_file: Path) -> None:
        """Basic dependency vulnerability check."""
        known_vulnerable = {
            'django<2.2': 'Django versions below 2.2 have known security issues',
            'flask<1.0': 'Flask versions below 1.0 have security vulnerabilities',
            'requests<2.20': 'Requests versions below 2.20 have CVE-2018-18074',
            'pyyaml<5.1': 'PyYAML versions below 5.1 have arbitrary code execution vulnerability'
        }
        
        content = requirements_file.read_text()
        for package, issue in known_vulnerable.items():
            if package.split('<')[0] in content.lower():
                self._add_vulnerability(
                    'dependency',
                    'medium',
                    issue,
                    'requirements.txt'
                )
    
    def _generate_security_report(self, output_dir: Path) -> None:
        """Generate security scan report."""
        report_path = output_dir / 'security-report.md'
        
        report = f"""# Security Scan Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

- **Security Score**: {self.security_score}/100
- **Total Issues**: {len(self.vulnerabilities)}
- **Critical**: {sum(1 for v in self.vulnerabilities if v['severity'] == 'critical')}
- **High**: {sum(1 for v in self.vulnerabilities if v['severity'] == 'high')}
- **Medium**: {sum(1 for v in self.vulnerabilities if v['severity'] == 'medium')}
- **Low**: {sum(1 for v in self.vulnerabilities if v['severity'] == 'low')}

## Vulnerabilities

"""
        
        # Group by severity
        for severity in ['critical', 'high', 'medium', 'low']:
            vulns = [v for v in self.vulnerabilities if v['severity'] == severity]
            if vulns:
                report += f"### {severity.title()} Severity\\n\\n"
                
                for vuln in vulns:
                    report += f"- **{vuln['type']}**: {vuln['description']}\\n"
                    report += f"  - File: `{vuln['file']}`\\n"
                    if vuln.get('line'):
                        report += f"  - Line: {vuln['line']}\\n"
                    report += "\\n"
        
        # Add recommendations
        report += """## Recommendations

1. **Fix Critical and High severity issues immediately**
2. **Review and update dependencies** to latest secure versions
3. **Enable security headers** for web applications
4. **Use parameterized queries** for database operations
5. **Avoid hardcoding secrets** - use environment variables
6. **Enable SSL verification** in production
7. **Disable debug mode** in production
8. **Implement input validation** for all user inputs

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security](https://python.readthedocs.io/en/latest/library/security_warnings.html)
- [npm Security Best Practices](https://docs.npmjs.com/packages-and-modules/securing-your-code)
"""
        
        report_path.write_text(report)
        self.logger.info(f"Security report saved to: {report_path}")
    
    def _display_security_summary(self) -> None:
        """Display security scan summary."""
        self.logger.info("=" * 60)
        self.logger.info("Security Scan Summary")
        self.logger.info("=" * 60)
        self.logger.info(f"Security Score: {self.security_score}/100")
        self.logger.info(f"Total Issues Found: {len(self.vulnerabilities)}")
        
        severity_counts = {
            'critical': sum(1 for v in self.vulnerabilities if v['severity'] == 'critical'),
            'high': sum(1 for v in self.vulnerabilities if v['severity'] == 'high'),
            'medium': sum(1 for v in self.vulnerabilities if v['severity'] == 'medium'),
            'low': sum(1 for v in self.vulnerabilities if v['severity'] == 'low')
        }
        
        for severity, count in severity_counts.items():
            if count > 0:
                symbol = '❌' if severity in ['critical', 'high'] else '⚠️'
                self.logger.info(f"{symbol} {severity.title()}: {count}")
        
        self.logger.info("=" * 60)
        
        if self.security_score < 70:
            self.logger.warning("⚠️  Security score is below 70. Please review the security report.")
    
    def _has_high_severity_issues(self) -> bool:
        """Check if there are high severity issues."""
        return any(v['severity'] in ['critical', 'high'] for v in self.vulnerabilities)


def register():
    """Register the plugin."""
    return SecurityScannerPlugin()
'''
    
    @staticmethod
    def create_plugin_package() -> str:
        """Create a plugin package template.
        
        Returns:
            Package structure template
        """
        return """# Plugin Package Structure

```
my-claude-builder-plugin/
├── src/
│   └── my_plugin/
│       ├── __init__.py
│       ├── plugin.py         # Main plugin class
│       ├── handlers.py       # Event handlers
│       └── utils.py          # Helper functions
├── tests/
│   └── test_plugin.py
├── examples/
│   └── example_config.yaml
├── README.md
├── setup.py
└── requirements.txt
```

## setup.py

```python
from setuptools import setup, find_packages

setup(
    name="claude-builder-my-plugin",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="My plugin for Claude Code Builder",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/claude-builder-my-plugin",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    install_requires=[
        "claude-code-builder>=2.0.0",
    ],
    entry_points={
        "claude_code_builder.plugins": [
            "my_plugin = my_plugin.plugin:register",
        ],
    },
)
```

## Plugin Development Guide

### 1. Available Hooks

- `on_load(context)` - Plugin initialization
- `on_pre_build(context)` - Before build starts
- `on_pre_phase(context)` - Before each phase
- `on_post_phase(context)` - After each phase
- `on_build_complete(context)` - After successful build
- `on_build_failed(context)` - On build failure
- `on_unload()` - Plugin cleanup

### 2. Context Object

The context object passed to hooks contains:

```python
{
    'project': ProjectSpec,      # Project specification
    'output_dir': Path,         # Output directory
    'phase': Phase,             # Current phase (if applicable)
    'phase_number': int,        # Current phase number
    'total_phases': int,        # Total number of phases
    'created_files': List[str], # Files created in phase
    'config': Dict,             # Plugin configuration
    'error': Exception,         # Error (if failed)
}
```

### 3. Plugin Configuration

Users can configure plugins in `.claude-code-builder.yaml`:

```yaml
plugins:
  - my_plugin

plugin_config:
  my_plugin:
    enabled: true
    option1: value1
    option2: value2
```

### 4. Best Practices

1. **Handle Errors Gracefully** - Don't crash the build
2. **Use Logging** - Use self.logger for output
3. **Be Performant** - Don't slow down builds
4. **Document Configuration** - Clear config options
5. **Version Compatibility** - Check Claude Builder version
6. **Clean Up Resources** - Use on_unload for cleanup

### 5. Testing Your Plugin

```python
import pytest
from my_plugin.plugin import MyPlugin

def test_plugin_initialization():
    plugin = MyPlugin()
    assert plugin.name == "my_plugin"
    assert plugin.version == "1.0.0"

def test_pre_build_hook():
    plugin = MyPlugin()
    context = {
        'project': MockProject(),
        'output_dir': Path('/tmp/test')
    }
    
    # Should not raise
    plugin.on_pre_build(context)
```

### 6. Publishing

1. Test thoroughly
2. Document all features
3. Create examples
4. Publish to PyPI
5. Submit to plugin registry

## Example Plugins

See the examples in this module for inspiration:
- Basic Plugin - Simple starting point
- Build Notifier - Send notifications
- Code Analyzer - Analyze code quality
- Deployment - Deploy to platforms
- Test Runner - Run tests automatically
- Documentation - Generate docs
- Metrics Collector - Track build metrics
- Security Scanner - Scan for vulnerabilities
"""


def create_plugin_examples(output_dir: Path) -> None:
    """Create all plugin examples.
    
    Args:
        output_dir: Output directory
    """
    plugins_dir = output_dir / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    
    # Save all plugin examples
    examples = PluginExample.get_all_examples()
    
    for name, code in examples.items():
        plugin_file = plugins_dir / f"{name}.py"
        plugin_file.write_text(code)
    
    # Create plugin package template
    package_file = plugins_dir / "plugin_package_template.md"
    package_file.write_text(PluginExample.create_plugin_package())
    
    # Create README
    readme = plugins_dir / "README.md"
    readme.write_text("""# Claude Code Builder Plugin Examples

This directory contains example plugins demonstrating how to extend Claude Code Builder.

## Available Examples

1. **basic_plugin.py** - Simple plugin structure with all hooks
2. **build_notifier.py** - Send notifications (email, Slack, webhooks)
3. **code_analyzer.py** - Analyze code quality and metrics
4. **deployment_plugin.py** - Deploy to various platforms
5. **test_runner.py** - Automatically run tests
6. **documentation_plugin.py** - Generate documentation
7. **metrics_collector.py** - Collect detailed build metrics
8. **security_scanner.py** - Scan for security vulnerabilities

## Using Plugins

### Method 1: Install from File

```bash
claude-code-builder plugin install ./plugins/basic_plugin.py
```

### Method 2: Install from Package

```bash
pip install claude-builder-plugin-name
```

### Method 3: Configure in Project

```yaml
# .claude-code-builder.yaml
plugins:
  - basic_plugin
  - build_notifier

plugin_config:
  build_notifier:
    slack:
      enabled: true
      webhook_url: https://hooks.slack.com/...
```

## Creating Your Own Plugin

1. Start with `basic_plugin.py` as a template
2. Implement the hooks you need
3. Add configuration options
4. Test with a real project
5. Package and distribute

See `plugin_package_template.md` for packaging instructions.

## Plugin Ideas

- **Git Integration** - Auto-commit after build
- **Database Migration** - Run migrations after deployment
- **API Testing** - Test API endpoints after build
- **Performance Monitor** - Track build performance over time
- **License Checker** - Verify dependency licenses
- **Changelog Generator** - Auto-generate CHANGELOG.md
- **Docker Builder** - Build and push Docker images
- **Cloud Deployer** - Deploy to AWS/GCP/Azure

## Contributing

If you create a useful plugin, consider:
1. Publishing to PyPI
2. Submitting a PR to add it to examples
3. Adding it to the plugin registry

Happy plugin development! 🚀
""")


if __name__ == "__main__":
    # Generate all plugin examples
    output_dir = Path("generated_plugins")
    create_plugin_examples(output_dir)
    print(f"Plugin examples created in: {output_dir}")
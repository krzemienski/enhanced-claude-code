"""Advanced project examples for Claude Code Builder."""
from pathlib import Path
from typing import Dict, Any, List


def get_blog_platform_spec() -> str:
    """Get blog platform specification.
    
    Returns:
        Markdown specification for a blog platform
    """
    return """# Blog Platform API

A comprehensive blogging platform with REST API and real-time features.

## Overview

A modern blogging platform that supports multiple authors, rich content editing, 
comments, and real-time notifications. Built with scalability and performance in mind.

## Features

### Core Features
- User registration and authentication (JWT-based)
- Multi-author support with roles (admin, editor, author, reader)
- Rich text editor with markdown support
- Draft and published post states
- Categories and tags
- Full-text search with ElasticSearch
- Comment system with threading
- Like and bookmark functionality
- RSS/Atom feeds

### Advanced Features
- Real-time notifications via WebSockets
- Email notifications
- Social media sharing
- SEO optimization
- Analytics dashboard
- Content moderation
- Rate limiting and abuse prevention
- Multi-language support (i18n)

## Technical Architecture

### Backend Stack
- Framework: FastAPI (Python 3.10+)
- Database: PostgreSQL with SQLAlchemy ORM
- Cache: Redis for session management and caching
- Search: ElasticSearch for full-text search
- Queue: Celery with RabbitMQ for async tasks
- Storage: S3-compatible object storage for media

### Security
- JWT authentication with refresh tokens
- OAuth2 social login (Google, GitHub)
- Rate limiting per endpoint
- Input validation and sanitization
- XSS and CSRF protection
- API key management for external integrations

### API Structure

#### Authentication Endpoints
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout
- POST /api/v1/auth/forgot-password
- POST /api/v1/auth/reset-password
- GET /api/v1/auth/verify-email/{token}

#### User Management
- GET /api/v1/users/me
- PUT /api/v1/users/me
- DELETE /api/v1/users/me
- GET /api/v1/users/{username}
- POST /api/v1/users/me/avatar

#### Blog Posts
- GET /api/v1/posts (with pagination, filtering, sorting)
- POST /api/v1/posts
- GET /api/v1/posts/{slug}
- PUT /api/v1/posts/{slug}
- DELETE /api/v1/posts/{slug}
- POST /api/v1/posts/{slug}/publish
- POST /api/v1/posts/{slug}/unpublish

#### Comments
- GET /api/v1/posts/{slug}/comments
- POST /api/v1/posts/{slug}/comments
- PUT /api/v1/comments/{id}
- DELETE /api/v1/comments/{id}
- POST /api/v1/comments/{id}/like

#### Search and Discovery
- GET /api/v1/search/posts
- GET /api/v1/tags
- GET /api/v1/categories
- GET /api/v1/trending

#### Real-time Features
- WebSocket /ws/notifications
- WebSocket /ws/comments/{post_slug}

## Data Models

### User
- id: UUID
- username: string (unique)
- email: string (unique)
- password_hash: string
- role: enum (admin, editor, author, reader)
- profile: JSON (bio, avatar_url, social_links)
- email_verified: boolean
- created_at: datetime
- updated_at: datetime

### Post
- id: UUID
- slug: string (unique)
- title: string
- content: text (markdown)
- excerpt: string
- author_id: UUID (FK -> User)
- status: enum (draft, published, archived)
- featured_image: string
- categories: M2M -> Category
- tags: M2M -> Tag
- meta: JSON (seo_title, seo_description, etc.)
- published_at: datetime
- created_at: datetime
- updated_at: datetime

### Comment
- id: UUID
- post_id: UUID (FK -> Post)
- parent_id: UUID (FK -> Comment, nullable)
- author_id: UUID (FK -> User)
- content: text
- status: enum (pending, approved, spam)
- created_at: datetime
- updated_at: datetime

## Performance Requirements

- API response time < 100ms for cached content
- < 500ms for database queries
- Support 10,000 concurrent users
- 99.9% uptime SLA
- Horizontal scaling capability

## Testing Strategy

- Unit tests for all business logic (>90% coverage)
- Integration tests for all API endpoints
- Load testing with Locust
- E2E tests for critical user flows
- Security testing with OWASP ZAP

## Deployment

- Dockerized application
- Kubernetes deployment manifests
- CI/CD with GitHub Actions
- Environment-based configuration
- Database migrations with Alembic
- Health check endpoints
- Prometheus metrics
- Structured logging with JSON

## Documentation

- OpenAPI/Swagger documentation
- API client SDKs (Python, JavaScript)
- Architecture decision records (ADRs)
- Deployment guides
- API versioning strategy
"""


def get_microservices_ecommerce_spec() -> str:
    """Get microservices e-commerce specification.
    
    Returns:
        Markdown specification for microservices architecture
    """
    return """# E-Commerce Microservices Platform

A scalable e-commerce platform built with microservices architecture.

## Overview

A modern e-commerce platform designed for high scalability, featuring independent 
services for different business domains, event-driven architecture, and cloud-native 
deployment.

## Architecture Overview

### Microservices

1. **API Gateway Service**
   - Route management
   - Authentication/Authorization
   - Rate limiting
   - Request/Response transformation
   - Circuit breaker

2. **User Service**
   - User registration/authentication
   - Profile management
   - JWT token generation
   - Password reset
   - OAuth integration

3. **Product Service**
   - Product catalog
   - Inventory management
   - Product search
   - Categories and attributes
   - Product recommendations

4. **Cart Service**
   - Shopping cart management
   - Session handling
   - Cart persistence
   - Price calculation

5. **Order Service**
   - Order processing
   - Order history
   - Status tracking
   - Invoice generation

6. **Payment Service**
   - Payment processing
   - Multiple payment gateways
   - Transaction management
   - Refund handling

7. **Notification Service**
   - Email notifications
   - SMS notifications
   - Push notifications
   - Notification templates

8. **Search Service**
   - Full-text search
   - Faceted search
   - Search suggestions
   - Search analytics

### Technical Stack

#### Languages and Frameworks
- API Gateway: Node.js with Express
- User Service: Python with FastAPI
- Product Service: Go with Gin
- Cart Service: Node.js with NestJS
- Order Service: Python with FastAPI
- Payment Service: Java with Spring Boot
- Notification Service: Python with FastAPI
- Search Service: Python with FastAPI + ElasticSearch

#### Infrastructure
- Container Orchestration: Kubernetes
- Service Mesh: Istio
- Message Queue: RabbitMQ / Apache Kafka
- API Gateway: Kong / Traefik
- Service Discovery: Consul
- Configuration: Consul KV / Kubernetes ConfigMaps

#### Databases
- User Service: PostgreSQL
- Product Service: PostgreSQL + Redis cache
- Cart Service: Redis
- Order Service: PostgreSQL
- Payment Service: PostgreSQL
- Search Service: ElasticSearch

#### Monitoring and Observability
- Metrics: Prometheus + Grafana
- Logging: ELK Stack (ElasticSearch, Logstash, Kibana)
- Tracing: Jaeger
- Health Checks: Custom endpoints

## Inter-Service Communication

### Synchronous Communication
- REST APIs for real-time operations
- gRPC for internal service communication
- Circuit breakers for fault tolerance

### Asynchronous Communication
- Event-driven architecture with Kafka
- Event sourcing for order processing
- CQRS pattern for read/write separation

### Event Examples
- UserRegistered
- OrderPlaced
- PaymentProcessed
- InventoryUpdated
- ProductViewed

## Security

### Authentication & Authorization
- JWT tokens with refresh mechanism
- OAuth2 for social login
- API key management
- Role-based access control (RBAC)

### Data Security
- Encryption at rest and in transit
- PCI compliance for payment data
- GDPR compliance for user data
- Regular security audits

## Scalability Patterns

### Horizontal Scaling
- Stateless services
- Database sharding
- Read replicas
- Cache-aside pattern

### Performance Optimization
- CDN for static assets
- Redis caching layer
- Database query optimization
- Lazy loading

## Deployment Strategy

### Kubernetes Manifests
- Deployments for each service
- Services for internal communication
- Ingress for external access
- ConfigMaps for configuration
- Secrets for sensitive data
- HPA for auto-scaling

### CI/CD Pipeline
- GitOps with ArgoCD
- Automated testing
- Blue-green deployments
- Canary releases
- Rollback capability

## Testing Strategy

### Testing Levels
- Unit tests per service
- Integration tests
- Contract testing with Pact
- End-to-end tests
- Performance testing
- Chaos engineering

### Test Coverage Goals
- Unit tests: >80%
- Integration tests: Critical paths
- E2E tests: Key user journeys

## Documentation

- API documentation per service
- Architecture diagrams
- Deployment guides
- Runbooks for operations
- Postman collections
"""


def get_ml_pipeline_spec() -> str:
    """Get machine learning pipeline specification.
    
    Returns:
        Markdown specification for ML pipeline
    """
    return """# Machine Learning Pipeline Platform

An end-to-end ML pipeline platform for model training, deployment, and monitoring.

## Overview

A comprehensive platform for managing the complete machine learning lifecycle, 
from data ingestion to model serving, with emphasis on reproducibility, 
scalability, and monitoring.

## Core Components

### Data Pipeline
- Data ingestion from multiple sources
- ETL/ELT processes
- Data validation and quality checks
- Feature engineering pipeline
- Data versioning with DVC
- Data catalog with metadata

### Model Development
- Experiment tracking with MLflow
- Hyperparameter optimization
- Distributed training support
- Model versioning
- A/B testing framework
- AutoML capabilities

### Model Serving
- REST API endpoints
- Batch prediction service
- Real-time streaming predictions
- Model registry
- Multi-model serving
- Edge deployment support

### Monitoring & Operations
- Model performance monitoring
- Data drift detection
- Prediction monitoring
- Alert system
- Automated retraining
- Model explainability

## Technical Architecture

### Technology Stack
- Language: Python 3.9+
- ML Frameworks: TensorFlow, PyTorch, Scikit-learn
- Pipeline Orchestration: Apache Airflow
- Model Tracking: MLflow
- Serving: TensorFlow Serving, TorchServe, FastAPI
- Feature Store: Feast
- Monitoring: Prometheus + Grafana
- Storage: S3-compatible object storage

### Infrastructure
- Container Platform: Kubernetes
- GPU Support: NVIDIA GPU operator
- Distributed Computing: Ray/Dask
- Message Queue: Apache Kafka
- Databases: PostgreSQL, MongoDB
- Cache: Redis

## Pipeline Stages

### 1. Data Ingestion
```python
# Example pipeline stage
class DataIngestionStage:
    sources: List[DataSource]
    validators: List[DataValidator]
    output_format: DataFormat
    
    def run(self):
        # Ingest from multiple sources
        # Validate data quality
        # Store in feature store
```

### 2. Feature Engineering
- Feature extraction
- Feature transformation
- Feature selection
- Feature store integration

### 3. Model Training
- Distributed training
- Hyperparameter tuning
- Cross-validation
- Model evaluation

### 4. Model Deployment
- Canary deployment
- Shadow mode
- A/B testing
- Rollback capability

## API Specifications

### Pipeline Management API
- POST /api/v1/pipelines - Create pipeline
- GET /api/v1/pipelines/{id} - Get pipeline status
- POST /api/v1/pipelines/{id}/run - Trigger pipeline
- GET /api/v1/pipelines/{id}/runs - Get run history

### Model Management API
- POST /api/v1/models - Register model
- GET /api/v1/models - List models
- POST /api/v1/models/{id}/deploy - Deploy model
- GET /api/v1/models/{id}/metrics - Get model metrics

### Prediction API
- POST /api/v1/predict/{model_id} - Single prediction
- POST /api/v1/predict/batch - Batch prediction
- WebSocket /ws/predict/{model_id} - Stream predictions

## Data Models

### Pipeline
- id: UUID
- name: string
- description: text
- stages: JSON
- schedule: string (cron)
- config: JSON
- created_at: datetime
- updated_at: datetime

### Model
- id: UUID
- name: string
- version: string
- framework: string
- metrics: JSON
- parameters: JSON
- artifacts_path: string
- status: enum
- created_at: datetime

### Experiment
- id: UUID
- name: string
- model_id: UUID
- parameters: JSON
- metrics: JSON
- tags: JSON
- status: enum
- created_at: datetime

## Monitoring Strategy

### Model Monitoring
- Prediction latency
- Throughput metrics
- Error rates
- Model accuracy over time
- Feature importance changes

### Data Monitoring
- Data quality metrics
- Schema changes
- Statistical drift
- Missing value patterns
- Outlier detection

### System Monitoring
- Resource utilization
- Queue depths
- API response times
- Error logs
- Cost tracking

## Security & Compliance

- Encrypted model storage
- API authentication
- Audit logging
- GDPR compliance
- Model governance
- Access control (RBAC)

## Deployment

### Development Environment
- Docker Compose setup
- Local Kubernetes (k3s/minikube)
- Mock data generators
- Jupyter notebooks

### Production Environment
- Kubernetes deployment
- Helm charts
- GitOps workflow
- Multi-region support
- Disaster recovery
"""


def get_realtime_collaboration_spec() -> str:
    """Get real-time collaboration platform specification.
    
    Returns:
        Markdown specification for collaboration platform
    """
    return """# Real-Time Collaboration Platform

A comprehensive platform for real-time document collaboration with video conferencing.

## Overview

A modern collaboration platform combining real-time document editing, video 
conferencing, screen sharing, and project management features. Built for remote 
teams with a focus on performance and user experience.

## Core Features

### Document Collaboration
- Real-time collaborative editing
- Multiple document types (text, spreadsheet, presentation)
- Version history with rollback
- Commenting and annotations
- Offline mode with sync
- Document templates

### Communication
- Video conferencing (up to 100 participants)
- Screen sharing with annotations
- Chat with message history
- Voice notes
- Reactions and emojis
- Threaded conversations

### Project Management
- Kanban boards
- Task assignments
- Due dates and reminders
- Time tracking
- Progress visualization
- Integration with calendar

### File Management
- Cloud storage integration
- File sharing with permissions
- Real-time file sync
- Preview for 50+ file types
- Search across all content

## Technical Architecture

### Frontend
- Framework: React with TypeScript
- State Management: Redux Toolkit
- Real-time: Socket.io client
- Video: WebRTC with SimpleWebRTC
- UI Library: Material-UI
- Editor: Quill.js with OT support

### Backend Services

#### Core API Service (Node.js + Express)
- User authentication
- Document management
- Permission handling
- REST APIs

#### Real-time Service (Node.js + Socket.io)
- WebSocket connections
- Operational transformation
- Presence management
- Event broadcasting

#### Media Service (Go)
- WebRTC signaling
- TURN/STUN server
- Recording capabilities
- Stream management

#### Storage Service (Python + FastAPI)
- File upload/download
- S3 integration
- Thumbnail generation
- Virus scanning

### Infrastructure
- Load Balancer: NGINX
- WebSocket: Socket.io with Redis adapter
- Database: PostgreSQL + MongoDB
- Cache: Redis
- Queue: Bull (Redis-based)
- Storage: S3-compatible

## Real-time Features

### Operational Transformation
```javascript
// Example OT implementation
class OperationalTransform {
  transform(op1, op2) {
    // Transform concurrent operations
    // Maintain consistency
  }
  
  apply(document, operation) {
    // Apply operation to document
    // Broadcast to other users
  }
}
```

### Presence System
- User cursors in documents
- Active user indicators
- Typing indicators
- User status (online/away/busy)

### Conflict Resolution
- Automatic conflict resolution
- Manual merge UI for complex conflicts
- Operation history
- Undo/redo with OT

## API Specifications

### Authentication
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/refresh
- POST /api/auth/logout

### Documents
- GET /api/documents
- POST /api/documents
- GET /api/documents/{id}
- PUT /api/documents/{id}
- DELETE /api/documents/{id}
- GET /api/documents/{id}/history
- POST /api/documents/{id}/restore

### Collaboration
- WebSocket /ws/document/{id}
- WebSocket /ws/presence
- POST /api/documents/{id}/comments
- POST /api/documents/{id}/share

### Video Conferencing
- POST /api/rooms
- GET /api/rooms/{id}
- WebSocket /ws/room/{id}
- POST /api/rooms/{id}/record

## Data Models

### User
- id: UUID
- email: string
- name: string
- avatar_url: string
- preferences: JSON
- created_at: datetime

### Document
- id: UUID
- title: string
- type: enum (text, spreadsheet, presentation)
- content: JSON
- owner_id: UUID
- permissions: JSON
- version: integer
- created_at: datetime
- updated_at: datetime

### Operation
- id: UUID
- document_id: UUID
- user_id: UUID
- operation: JSON
- timestamp: datetime
- version: integer

## Performance Requirements

- Document load time < 2s
- Operation latency < 100ms
- Video call connection < 3s
- Support 10,000 concurrent users
- 99.95% uptime

## Security

### Authentication
- JWT with refresh tokens
- OAuth2 (Google, Microsoft)
- Two-factor authentication
- Session management

### Authorization
- Document-level permissions
- Role-based access
- Sharing controls
- Guest access

### Data Security
- End-to-end encryption for video
- Encryption at rest
- Secure file sharing
- Audit logs

## Scalability

### Horizontal Scaling
- Microservices architecture
- Load balancing
- Database sharding
- CDN for static assets

### Performance Optimization
- Connection pooling
- Lazy loading
- Delta sync
- Compression

## Testing Strategy

- Unit tests for OT algorithms
- Integration tests for real-time features
- Load testing for concurrent users
- E2E tests for user workflows
- Security penetration testing

## Deployment

### Development
```yaml
# docker-compose.yml
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
  
  api:
    build: ./api
    environment:
      - DATABASE_URL=postgresql://...
    
  realtime:
    build: ./realtime
    environment:
      - REDIS_URL=redis://...
```

### Production
- Kubernetes deployment
- Auto-scaling policies
- Multi-region deployment
- Blue-green deployments
- Monitoring and alerting
"""


class AdvancedProjectExample:
    """Advanced project example demonstrations."""
    
    @staticmethod
    def get_examples() -> Dict[str, Dict[str, Any]]:
        """Get all advanced project examples.
        
        Returns:
            Dictionary of example configurations
        """
        return {
            'blog_platform': {
                'name': 'Blog Platform API',
                'description': 'Full-featured blogging platform with real-time features',
                'difficulty': 'advanced',
                'duration': '2-3 hours',
                'spec': get_blog_platform_spec(),
                'phases': 12,
                'key_technologies': [
                    'FastAPI', 'PostgreSQL', 'Redis', 
                    'ElasticSearch', 'WebSockets', 'Celery'
                ]
            },
            'microservices_ecommerce': {
                'name': 'E-Commerce Microservices',
                'description': 'Scalable e-commerce platform with microservices',
                'difficulty': 'expert',
                'duration': '4-5 hours',
                'spec': get_microservices_ecommerce_spec(),
                'phases': 15,
                'key_technologies': [
                    'Multiple languages', 'Kubernetes', 'Kafka',
                    'Service Mesh', 'API Gateway', 'CQRS'
                ]
            },
            'ml_pipeline': {
                'name': 'ML Pipeline Platform',
                'description': 'End-to-end machine learning platform',
                'difficulty': 'expert',
                'duration': '3-4 hours',
                'spec': get_ml_pipeline_spec(),
                'phases': 14,
                'key_technologies': [
                    'MLflow', 'Airflow', 'TensorFlow',
                    'Kubernetes', 'Feature Store', 'Ray'
                ]
            },
            'realtime_collaboration': {
                'name': 'Real-Time Collaboration',
                'description': 'Collaboration platform with video and documents',
                'difficulty': 'expert',
                'duration': '4-5 hours',
                'spec': get_realtime_collaboration_spec(),
                'phases': 16,
                'key_technologies': [
                    'WebRTC', 'Socket.io', 'Operational Transform',
                    'React', 'Node.js', 'Redis'
                ]
            }
        }
    
    @staticmethod
    def get_deployment_configs() -> Dict[str, str]:
        """Get deployment configuration examples.
        
        Returns:
            Dictionary of deployment configs
        """
        return {
            'kubernetes': """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ service_name }}
  namespace: {{ namespace }}
spec:
  replicas: {{ replicas }}
  selector:
    matchLabels:
      app: {{ service_name }}
  template:
    metadata:
      labels:
        app: {{ service_name }}
    spec:
      containers:
      - name: {{ service_name }}
        image: {{ image }}:{{ tag }}
        ports:
        - containerPort: {{ port }}
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: {{ service_name }}-secrets
              key: database-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: {{ port }}
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: {{ port }}
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: {{ service_name }}
  namespace: {{ namespace }}
spec:
  selector:
    app: {{ service_name }}
  ports:
  - protocol: TCP
    port: 80
    targetPort: {{ port }}
  type: ClusterIP
""",
            'docker_compose': """version: '3.8'

services:
  api:
    build:
      context: ./api
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/dbname
      - REDIS_URL=redis://redis:6379
      - ELASTICSEARCH_URL=http://elasticsearch:9200
    depends_on:
      - db
      - redis
      - elasticsearch
    volumes:
      - ./api:/app
    command: uvicorn main:app --reload --host 0.0.0.0

  db:
    image: postgres:14
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=dbname
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  elasticsearch:
    image: elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api

volumes:
  postgres_data:
  redis_data:
  es_data:
""",
            'github_actions': """name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        pytest --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: |
          ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
          ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - name: Deploy to Kubernetes
      uses: azure/k8s-deploy@v4
      with:
        manifests: |
          k8s/deployment.yaml
          k8s/service.yaml
        images: |
          ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
"""
        }
    
    @staticmethod
    def create_monitoring_setup() -> Dict[str, str]:
        """Create monitoring configuration examples.
        
        Returns:
            Dictionary of monitoring configs
        """
        return {
            'prometheus_config': """global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

rule_files:
  - "alerts/*.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'api-service'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
""",
            'grafana_dashboard': """{
  "dashboard": {
    "title": "Application Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Response Time",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Active Users",
        "targets": [
          {
            "expr": "active_users_total"
          }
        ],
        "type": "stat"
      }
    ]
  }
}""",
            'alerts': """groups:
  - name: api_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: High error rate detected
          description: "Error rate is {{ $value }} errors per second"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High response time
          description: "95th percentile response time is {{ $value }} seconds"

      - alert: DatabaseConnectionFailure
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: Database connection failed
          description: "PostgreSQL is not accessible"
"""
        }


def create_advanced_example(output_dir: Path) -> None:
    """Create advanced example files.
    
    Args:
        output_dir: Output directory for examples
    """
    examples_dir = output_dir / "advanced"
    examples_dir.mkdir(parents=True, exist_ok=True)
    
    examples = AdvancedProjectExample.get_examples()
    
    for name, config in examples.items():
        # Write specification
        spec_path = examples_dir / f"{name}.md"
        spec_path.write_text(config['spec'])
        
        # Create build script
        build_script = examples_dir / f"build_{name}.sh"
        build_script.write_text(f"""#!/bin/bash
# Build {config['name']} example

set -e

echo "Building {config['name']}..."
echo "This is an advanced project that will take {config['duration']} to build."
echo ""
echo "Key technologies: {', '.join(config['key_technologies'])}"
echo ""

# Check prerequisites
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Error: ANTHROPIC_API_KEY not set"
    exit 1
fi

# Build with specified phases
claude-code-builder build {name}.md \\
    --output-dir ./{name}-output \\
    --phases {config['phases']} \\
    "$@"

echo ""
echo "Build complete! Check ./{name}-output for the generated project."
""")
        build_script.chmod(0o755)
    
    # Create README
    readme = examples_dir / "README.md"
    readme.write_text("""# Advanced Project Examples

This directory contains advanced, production-ready project examples demonstrating 
complex architectures and modern development practices.

## Examples

### Blog Platform (`blog_platform.md`)
A comprehensive blogging platform with:
- Multi-author support
- Real-time features
- Full-text search
- Advanced security

**Technologies**: FastAPI, PostgreSQL, Redis, ElasticSearch, WebSockets

### E-Commerce Microservices (`microservices_ecommerce.md`)
A scalable e-commerce platform featuring:
- Microservices architecture
- Multiple programming languages
- Event-driven communication
- Container orchestration

**Technologies**: Kubernetes, Kafka, Service Mesh, Multiple databases

### ML Pipeline Platform (`ml_pipeline.md`)
An end-to-end machine learning platform with:
- Experiment tracking
- Model versioning
- Distributed training
- Model monitoring

**Technologies**: MLflow, Airflow, TensorFlow, Kubernetes

### Real-Time Collaboration (`realtime_collaboration.md`)
A collaboration platform featuring:
- Real-time document editing
- Video conferencing
- Operational transformation
- Presence system

**Technologies**: WebRTC, Socket.io, React, Node.js

## Building Advanced Projects

These projects require more time and resources to build:

```bash
# Allocate more time and resources
claude-code-builder build <project>.md --phases 15 --max-tokens 150000

# Build with custom configuration
claude-code-builder build <project>.md --config advanced.yaml
```

## Prerequisites

- Anthropic API key with sufficient credits
- At least 8GB RAM recommended
- Understanding of the technologies involved
- Patience - these builds can take 2-5 hours

## Customization Tips

1. **Simplify First**: Start by removing some features to test the core
2. **Phase Control**: Use fewer phases for faster initial builds
3. **Custom Instructions**: Add architectural preferences
4. **Incremental Building**: Build core services first, then add others

## Deployment

Each project includes deployment configurations:
- Docker Compose for development
- Kubernetes manifests for production
- CI/CD pipeline examples
- Monitoring setup

## Support

For issues or questions:
1. Check the generated project's README
2. Review the build logs
3. Consult the architecture documentation
4. Open an issue on GitHub
""")


if __name__ == "__main__":
    # Example usage
    examples_dir = Path("generated_advanced_examples")
    create_advanced_example(examples_dir)
    print(f"Advanced examples generated in: {examples_dir}")
# E-commerce REST API

A comprehensive REST API for an e-commerce platform with user management, product catalog, and order processing.

# Description

This project implements a production-ready REST API for an e-commerce platform. The API provides complete functionality for user authentication, product management, shopping cart operations, order processing, payment integration, and administrative functions. Built with modern Python frameworks and following RESTful best practices, it's designed for scalability, security, and performance.

# Features

### User Management
- User registration with email verification
- JWT-based authentication
- Password reset functionality
- User profile management
- Role-based access control (customer, vendor, admin)
- OAuth2 social login integration

### Product Catalog
- Product CRUD operations
- Category and subcategory management
- Product search and filtering
- Image upload and management
- Inventory tracking
- Product variants (size, color, etc.)
- Product reviews and ratings

### Shopping Cart
- Add/remove items from cart
- Update quantities
- Cart persistence for logged-in users
- Guest cart functionality
- Cart merging on login
- Apply discount codes

### Order Processing
- Order creation from cart
- Order status tracking
- Order history
- Invoice generation
- Shipping address management
- Multiple payment methods

### Payment Integration
- Stripe payment processing
- PayPal integration
- Refund handling
- Payment webhook handling
- Transaction logging
- PCI compliance

### Admin Features
- Dashboard with analytics
- User management
- Product approval workflow
- Order management
- Report generation
- System configuration

# Technologies
- Python 3.9+ (required)
- FastAPI 0.100+ (required)
- PostgreSQL 14+ (required)
- Redis 7.0+ (required)
- SQLAlchemy 2.0+ (required)
- Alembic 1.12+ (required)
- Pydantic 2.0+ (required)
- JWT (python-jose) (required)
- Stripe SDK (required)
- AWS S3 (optional)
- Elasticsearch 8.0+ (optional)
- Docker (required)

# API Endpoints

### Authentication
- POST /api/auth/register - User registration
- POST /api/auth/login - User login
- POST /api/auth/refresh - Refresh JWT token
- POST /api/auth/logout - User logout
- POST /api/auth/forgot-password - Request password reset
- POST /api/auth/reset-password - Reset password

### Users
- GET /api/users/profile - Get user profile
- PUT /api/users/profile - Update profile
- GET /api/users/orders - Get user orders
- GET /api/users/addresses - Get saved addresses
- POST /api/users/addresses - Add new address

### Products
- GET /api/products - List products (with pagination)
- GET /api/products/{id} - Get product details
- GET /api/products/search - Search products
- POST /api/products - Create product (vendor)
- PUT /api/products/{id} - Update product (vendor)
- DELETE /api/products/{id} - Delete product (vendor)
- POST /api/products/{id}/reviews - Add review

### Categories
- GET /api/categories - List all categories
- GET /api/categories/{id}/products - Products by category

### Cart
- GET /api/cart - Get current cart
- POST /api/cart/items - Add item to cart
- PUT /api/cart/items/{id} - Update cart item
- DELETE /api/cart/items/{id} - Remove from cart
- POST /api/cart/checkout - Proceed to checkout

### Orders
- POST /api/orders - Create order
- GET /api/orders/{id} - Get order details
- GET /api/orders - List user orders
- PUT /api/orders/{id}/cancel - Cancel order
- GET /api/orders/{id}/invoice - Download invoice

### Payments
- POST /api/payments/create-intent - Create payment intent
- POST /api/payments/confirm - Confirm payment
- POST /api/webhooks/stripe - Stripe webhook endpoint

### Admin
- GET /api/admin/dashboard - Dashboard statistics
- GET /api/admin/users - List all users
- PUT /api/admin/users/{id} - Update user
- GET /api/admin/orders - List all orders
- PUT /api/admin/orders/{id}/status - Update order status

# Technical Requirements

### Performance
- Response time < 100ms for most endpoints
- Support 10,000 concurrent users
- Database query optimization
- Redis caching for frequently accessed data
- CDN integration for static assets

### Security
- HTTPS only with TLS 1.3
- Rate limiting per endpoint
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CORS configuration
- API key authentication for webhooks
- Audit logging

### Scalability
- Horizontal scaling support
- Database connection pooling
- Async request handling
- Message queue for background jobs
- Microservices-ready architecture

### Monitoring
- Health check endpoints
- Prometheus metrics
- Structured logging
- Error tracking with Sentry
- Performance monitoring

# Database Schema

### Users Table
- id (UUID, primary key)
- email (unique)
- password_hash
- full_name
- role
- is_active
- created_at
- updated_at

### Products Table
- id (UUID, primary key)
- name
- description
- price
- category_id
- vendor_id
- inventory_count
- images (JSON)
- created_at
- updated_at

### Orders Table
- id (UUID, primary key)
- user_id
- status
- total_amount
- shipping_address
- payment_method
- created_at
- updated_at

### Order Items Table
- id (UUID, primary key)
- order_id
- product_id
- quantity
- price
- subtotal

# Implementation Details

### Authentication Flow
1. User registers with email/password
2. Email verification sent
3. User logs in, receives JWT token
4. Token included in Authorization header
5. Token refresh before expiration

### Payment Flow
1. User proceeds to checkout
2. Create Stripe payment intent
3. Frontend handles payment
4. Webhook confirms payment
5. Order status updated
6. Email confirmation sent

### Error Handling
- Consistent error response format
- Proper HTTP status codes
- Detailed error messages in development
- Generic messages in production
- Request ID for tracking
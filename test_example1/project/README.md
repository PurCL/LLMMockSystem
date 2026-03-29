# DocuServe

A workspace for uploading, storing, managing, and viewing documents, enabling teams or individuals to share files in a centralized repository.

## 🏗️ Architecture
```
┌─────────────────┐    ┌───────────────────┐    ┌─────────────────┐
│ React Frontend  │◄──►│  FastAPI Backend  │◄──►│  PostgreSQL DB  │
│  (Port 5173)    │    │   (Port 8000)     │    │   (Port 5432)   │
└─────────────────┘    └───────────────────┘    └─────────────────┘
```

## 📋 API Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/documents/upload` | Upload a new document. |
| `GET` | `/api/documents` | Retrieve a list of all documents. |
| `GET` | `/api/documents/{id}` | Retrieve metadata for a specific document. |
| `GET` | `/api/documents/{id}/view` | View the content of a specific document. |
| `DELETE` | `/api/documents/{id}` | Permanently delete a document. |

## 🛠️ Tech Stack

### Backend
*   **Framework**: FastAPI
*   **ORM / DB Library**: SQLModel
*   **Database**: PostgreSQL 15
*   **Language/Runtime**: Python 3.10+
*   **Server**: Uvicorn

### Frontend
*   **Framework**: React
*   **Build Tool**: Vite
*   **Language**: TypeScript
*   **UI Libraries**: TailwindCSS, Lucide React
*   **Runtime**: Node.js

### Infrastructure
*   **Containerization**: Docker
*   **Database Server**: PostgreSQL

## 🗄️ Database Schema

### Table: `document`
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | Integer | Primary Key (Auto-increment) |
| `name` | String | Name of the document (Indexed) |
| `size` | Integer | Size of the document in bytes |
| `content_type` | String | MIME type of the document |
| `path` | String | File system path to the stored document |
| `owner_id` | Integer | ID of the document owner |
| `last_modified_by`| String | Username of the last modifier |
| `extracted_text` | String | Text content extracted from the document |
| `created_at` | DateTime | Timestamp of creation |

## � Quick Start

### Prerequisites
*   Docker & Docker Compose
*   Git
*   Node.js (optional, for local development)

### 1. Clone and Start
```bash
git clone <repository-url>
cd dms
# Start the application
docker-compose up -d --build
```

### 2. Access the Application
*   **Frontend**: [http://localhost:5173](http://localhost:5173)
*   **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
*   **Database**: `localhost:5432`

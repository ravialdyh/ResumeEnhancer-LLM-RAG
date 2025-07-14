# Resume Optimization Tool

## Overview

This is a Streamlit-based resume optimization application that uses AI-powered analysis to help users enhance their resumes. The system leverages Google's Gemini AI model, Retrieval-Augmented Generation (RAG) techniques, and document parsing capabilities to provide intelligent resume analysis and optimization suggestions.

## User Preferences

- Preferred communication style: Simple, everyday language
- UI Preference: Single-page layout instead of tabbed interface
- Sidebar Preference: Collapsible sidebar to save space

## System Architecture

The application follows a modular Python architecture with the following key design decisions:

### Frontend Architecture
- **Technology**: Streamlit web framework
- **Rationale**: Chosen for rapid prototyping and ease of deployment for AI/ML applications
- **Layout**: Wide layout with collapsible sidebar and single-page dynamic interface
- **UI Design**: Progressive disclosure - shows input form initially, then analysis and comparison as user completes steps
- **State Management**: Uses Streamlit's session state for maintaining user data across interactions
- **Navigation**: Dynamic content based on completion status rather than traditional tabs

### Backend Architecture
- **Structure**: Utility-based modular design with separate classes for different functionalities
- **AI Integration**: Google Gemini 2.5 Flash model for natural language processing and analysis
- **Document Processing**: Multi-format support (PDF, DOCX) with fallback parsing strategies
- **RAG System**: FAISS vector database for similarity search and context retrieval
- **Database**: PostgreSQL for persistent storage of analysis history and session tracking

## Key Components

### 1. Document Parser (`utils/document_parser.py`)
- **Purpose**: Extracts text from PDF and DOCX files
- **Libraries**: PyMuPDF, pdfplumber, PyPDF2 for PDF parsing; python-docx for DOCX files
- **Fallback Strategy**: Multiple PDF parsing libraries to handle different PDF formats including image-based PDFs
- **Error Handling**: Graceful degradation with informative error messages and manual text input option

### 2. RAG System (`utils/rag_system.py`)
- **Purpose**: Implements Retrieval-Augmented Generation for contextual analysis
- **Vector Store**: FAISS (Facebook AI Similarity Search) for efficient similarity search
- **Embeddings**: SentenceTransformers (all-MiniLM-L6-v2 model) for text embeddings
- **Chunking Strategy**: Overlapping text chunks to maintain context
- **Fallback**: Graceful operation even without FAISS/SentenceTransformers

### 3. Resume Analyzer (`utils/resume_analyzer.py`)
- **Purpose**: Core AI analysis engine using Gemini model
- **Integration**: Combines RAG system with Gemini AI for contextual analysis
- **Analysis Features**: Skills matching, keyword optimization, formatting suggestions
- **Output**: Structured analysis results with scores and recommendations

### 4. Text Processor (`utils/text_processor.py`)
- **Purpose**: Text preprocessing and analysis utilities
- **Features**: 
  - Text chunking for RAG processing
  - Keyword extraction and matching
  - Resume section identification
  - Skills categorization (technical vs. soft skills)
- **Skills Database**: Predefined lists of common technical and soft skills

### 5. Main Application (`app.py`)
- **Purpose**: Streamlit frontend orchestrating all components
- **Session Management**: Maintains state for resume text, job descriptions, and analysis results
- **User Interface**: File upload, text input, and results display
- **Database Integration**: Persistent storage of analysis history and session tracking

### 6. Database Layer (`database/`)
- **Models** (`models.py`): SQLAlchemy models for resume analyses, user sessions, and analysis history
- **Service** (`service.py`): Database operations including saving analyses, tracking sessions, and retrieving history
- **Schema**: PostgreSQL tables for persistent data storage with JSON fields for complex analysis results

## Data Flow

1. **Document Input**: Users upload resume files (PDF/DOCX) or paste text
2. **Text Extraction**: DocumentParser extracts text from uploaded files
3. **Job Description Input**: Users provide job description for comparison
4. **RAG Index Building**: Job requirements are processed and indexed using FAISS
5. **Context Retrieval**: Relevant job requirements are retrieved for analysis
6. **AI Analysis**: Gemini model analyzes resume against job requirements with RAG context
7. **Results Display**: Analysis results, scores, and optimization suggestions are presented
8. **Iterative Improvement**: Users can refine and re-analyze their resumes

## External Dependencies

### Required Dependencies
- **streamlit**: Web framework for the user interface
- **google-genai**: Google Gemini AI integration
- **PyPDF2/pdfplumber**: PDF document parsing
- **python-docx**: DOCX document parsing
- **sentence-transformers**: Text embeddings for RAG system
- **faiss-cpu**: Vector similarity search
- **numpy**: Numerical operations

### Optional Dependencies
- Libraries are imported with try-catch blocks to allow graceful degradation
- Missing dependencies result in limited functionality rather than application failure

### Environment Variables
- **GEMINI_API_KEY**: Required for Google Gemini AI integration
- Application checks for API key presence and provides user feedback

## Deployment Strategy

### Development Setup
- Environment variable configuration for API keys
- Modular structure allows for easy testing of individual components
- Logging integration for debugging and monitoring

### Production Considerations
- API key management through environment variables
- Error handling and graceful degradation for missing optional dependencies
- Session state management for user data persistence
- Wide layout optimized for resume document display

### Scalability Approach
- Modular design allows for easy component replacement or enhancement
- RAG system can be scaled with different vector databases
- AI model can be swapped or multiple models can be integrated
- Document parsing supports multiple formats with extensible architecture

The application prioritizes user experience with fallback mechanisms, clear error messaging, and intuitive interface design while maintaining robust AI-powered analysis capabilities.
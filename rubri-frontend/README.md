# Rubri Frontend

A modern, professional frontend for the AI-powered interview question generation platform.

## Features

🎯 **Dual Input Interface**
- File upload (PDF, DOC, DOCX, TXT) with drag-and-drop
- Direct text input for job descriptions and resumes
- Real-time validation and file preview

🤖 **AI-Powered Generation**
- Integration with sophisticated 5-agent backend system
- Real-time progress tracking with stage indicators
- Comprehensive error handling and retry logic

📊 **Rich Report Viewer**
- Markdown rendering with syntax highlighting
- Structured display of interview questions and guidance
- Export capabilities (PDF, shareable links)
- Key insights and metrics visualization

🎨 **Professional Design**
- Modern, clean interface with Tailwind CSS
- Fully responsive design for desktop and mobile
- Professional color scheme suitable for corporate use
- Smooth animations and transitions

## Tech Stack

- **React 18** with TypeScript for type safety
- **Vite** for fast development and building
- **Tailwind CSS** for styling and responsive design
- **React Markdown** for report rendering
- **Lucide React** for consistent iconography
- **React Hook Form** with Zod validation
- **Axios** for API communication
- **React Dropzone** for file uploads

## Quick Start

### Prerequisites
- Node.js 18+ 
- npm or yarn
- Running Rubri backend on port 8000

### Installation

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env to match your backend URL
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

4. **Open in browser**
   ```
   http://localhost:5173
   ```

### Backend Setup
Make sure the Rubri backend is running:
```bash
cd ../  # Go to backend directory
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Project Structure

```
src/
├── components/           # Reusable UI components
│   ├── ui/              # Basic UI components (Button, Input, etc.)
│   ├── forms/           # Form components (FileUpload, TextInput)
│   ├── layout/          # Layout components (Header, Footer)
│   ├── generation/      # Progress tracking components
│   └── report/          # Report display components
├── pages/               # Main application pages
│   ├── HomePage.tsx     # Landing page with features
│   └── GeneratorPage.tsx # Main generation interface
├── services/            # API integration
│   └── api.ts           # Backend API client
├── types/               # TypeScript type definitions
│   └── api.ts           # API response/request types
└── styles/              # Global styles and Tailwind config
```

## Key Components

### Input Interface
- **InputToggle**: Switch between file upload and text input
- **FileUploadForm**: Drag-and-drop file upload with validation
- **TextInputForm**: Direct text input with character counting

### Generation Flow
- **ProgressTracker**: Real-time progress with stage indicators
- **API Integration**: Handles file uploads and question generation
- **Error Handling**: User-friendly error messages and retry options

### Report Display
- **ReportViewer**: Comprehensive markdown report rendering
- **Metrics Display**: Key statistics and insights
- **Export Options**: PDF and shareable link generation

## User Journey

1. **Landing Page**: Professional homepage with features and benefits
2. **Input Selection**: Choose between file upload or text input
3. **Document Upload**: Drag-and-drop files or paste text content
4. **Position Title**: Enter the job position being interviewed for
5. **AI Generation**: Real-time progress tracking with stage updates
6. **Results Display**: Comprehensive report with questions and guidance
7. **Export Options**: PDF download or shareable link generation

## Development Commands

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type checking
npx tsc --noEmit
```

## Environment Variables

```bash
# API Configuration
VITE_API_BASE_URL=http://localhost:8000

# Development settings
VITE_ENV=development
```

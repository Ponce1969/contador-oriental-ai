# PRODUCT_SPEC.md - Contador Oriental

## Purpose
Family expense tracking application with AI assistance for Uruguayan users. 
Manages household expenses, income, and provides AI-powered financial advice.

## Target Users
- Uruguayan families
- Home accounting managers
- Users seeking AI assistance for expense categorization and tax advice

## Core Features

### 1. Expense Management
- Add/edit/delete expenses with categories (Almacén, Hogar, Servicios, etc.)
- Monthly expense tracking
- Recurring expenses support
- OCR ticket upload via mobile

### 2. Income Tracking
- Multiple income sources per family
- Monthly income summaries

### 3. AI Advisor (Contador Virtual)
- Natural language queries about expenses
- Category-based analysis
- Tax law context (RAG with Uruguayan tax knowledge)
- Vector memory for conversation context

### 4. OCR Ticket Processing
- Mobile ticket upload via QR code
- Tesseract OCR text extraction
- Gemma2 AI parsing (monto, fecha, comercio, items)
- Session-based workflow

### 5. Multi-Family Support
- Family registration and management
- Per-family data isolation (familia_id)
- Role-based access

## User Flows

### Add Expense (Manual)
1. Login → Gastos → "+" button
2. Fill form: monto, descripción, fecha, categoría
3. Save → Expense added

### Add Expense (OCR)
1. Login → Gastos → Camera icon
2. Scan QR with mobile device
3. Mobile: Upload ticket photo
4. OCR processes → Gemma2 parses
5. Mobile shows "Listo" → User confirms
6. Flet polls result → Shows confirmation
7. User confirms → Expense saved

### AI Consultation
1. Login → Contador
2. Type question in natural language
3. AI responds with context-aware advice

## Success Criteria
- Expenses correctly saved to PostgreSQL
- OCR extracts monto/fecha/comercio from tickets
- AI responds accurately to expense queries
- Multi-family data isolation maintained
- Web and desktop modes functional

## Out of Scope
- Real payment processing
- Bank API integrations
- Multi-currency support

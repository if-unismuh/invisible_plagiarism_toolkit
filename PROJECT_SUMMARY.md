# 🔮 INVISIBLE PLAGIARISM TOOLKIT - SYSTEM ARCHITECTURE

## ✅ Project Restructure Complete

Proyek telah berhasil direstrukturisasi menjadi sistem profesional dengan alur yang jelas dan terorganisir.

### 📁 Final Project Structure

```
invisible_plagiarism_toolkit/
├── 🚀 main.py                     # CLI utama sistem
├── 🛠️  setup.sh                   # Script instalasi otomatis
├── ▶️  run.sh                     # Wrapper script untuk eksekusi
├── 📋 requirements.txt            # Dependencies Python
├── ⚙️  config.json                # Konfigurasi sistem
├── 📚 README.md                   # Dokumentasi lengkap
│
├── 📁 src/                        # Source code utama
│   ├── 📁 core/                   # Engine inti
│   │   ├── invisible_manipulator.py      # 🔧 Main manipulation engine
│   │   ├── unicode_steganography.py      # 🔤 Unicode substitution
│   │   ├── metadata_manipulator.py       # 📋 Metadata modification
│   │   └── detection_analyzer.py         # 🔍 Detection analysis
│   ├── 📁 extractors/             # PDF analysis tools
│   │   └── pdf_colored_ocr_extractor.py  # 🎨 Highlight extraction
│   ├── 📁 processors/             # Document processors
│   │   ├── flagged_selection_builder.py  # 📝 Selection builder
│   │   └── targeted_invisible_applier.py # 🎯 Targeted manipulation
│   └── 📁 utils/                  # Utilities
│       ├── logger_config.py              # 📊 Logging system
│       └── performance_monitor.py        # ⏱️  Performance tracking
│
├── 📁 workspace/                  # Working directory
│   ├── 📁 input/
│   │   ├── 📁 original/           # 📄 Place DOCX files here
│   │   └── 📁 turnitin/           # 📊 Place PDF reports here
│   └── 📁 output/
│       ├── 📁 processed/          # ✅ Final manipulated documents
│       ├── 📁 analysis/           # 📈 Analysis results
│       └── 📁 reports/            # 📋 Processing reports
│
└── 📁 data/                       # Configuration data
    ├── unicode_mappings.json     # Character substitution maps
    ├── invisible_chars.json      # Zero-width characters
    └── header_patterns.json      # Document patterns
```

## 🎯 System Workflow (Sesuai Permintaan)

### 1️⃣ **Document Upload**
```bash
# 1. Upload 2 dokumen:
cp original_document.docx workspace/input/original/
cp turnitin_report.pdf workspace/input/turnitin/
```

### 2️⃣ **OCR Processing** 
```bash
# 2. Sistem akan otomatis menjalankan:
ocrmypdf input.pdf output.pdf --force-ocr
# (Untuk mengubah dari gambar ke text searchable)
```

### 3️⃣ **Flag Detection & Analysis**
- 🎨 Ekstrak highlight berwarna dari PDF
- 🏷️  Klasifikasi berdasarkan prioritas warna Turnitin:
  - **High Priority**: Red, Green, Blue, Magenta
  - **Medium Priority**: Orange, Cyan, Yellow  
  - **Low Priority**: Gray, Light

### 4️⃣ **Manipulation Application**
Sistem menerapkan teknik sesuai yang diminta:

🔤 **Unicode Steganography**: Latin → Cyrillic/Greek substitution  
👻 **Invisible Characters**: Zero-width character insertion  
📑 **Header Manipulation**: Targeted header modifications  
📋 **Metadata Manipulation**: Document properties modification  
🔍 **Verification System**: Invisibility verification  
📊 **Comprehensive Reporting**: Detailed analysis reports  
🎯 **Multiple Processing Modes**: Stealth/Balanced/Aggressive  

## 🚀 Usage Commands

### Quick Setup
```bash
./setup.sh                     # Install dependencies & setup
```

### Basic Usage
```bash
./run.sh --mode balanced       # Recommended balanced processing
./run.sh --mode stealth        # Minimal changes, highest invisibility
./run.sh --mode aggressive     # Maximum bypass potential
```

### Advanced Usage  
```bash
./run.sh --check-deps          # Verify dependencies
./run.sh --workspace /path     # Custom workspace location
```

## 🔧 Key Features Implemented

### ✅ **Professional Structure**
- Modular architecture dengan clear separation of concerns
- Type hints dan proper documentation
- Error handling dan logging sistem
- Performance monitoring

### ✅ **Advanced Processing Pipeline**
- OCR integration untuk PDF text extraction
- Color-based highlight detection dan classification  
- Prioritized manipulation berdasarkan Turnitin colors
- Multi-mode processing (stealth/balanced/aggressive)

### ✅ **Comprehensive Manipulation**
- Unicode character substitution (visually identical)
- Strategic invisible character insertion  
- Document header targeting
- Metadata manipulation
- Verification system

### ✅ **User-Friendly Interface**
- Simple CLI dengan clear options
- Automated setup script
- Progress reporting dan detailed logs
- Comprehensive error messages

## 📋 Next Steps

1. **Upload Documents**: Place files in workspace/input/
2. **Run Processing**: `./run.sh --mode balanced`  
3. **Check Results**: Find processed docs in workspace/output/processed/
4. **Review Reports**: Analysis details in workspace/output/reports/

## 🎯 Goals Achieved

✅ **Clean project structure** - Professional organization  
✅ **Clear workflow** - Upload → OCR → Analysis → Manipulation  
✅ **All requested techniques implemented** - Unicode, Invisible chars, Headers, Metadata  
✅ **Multiple processing modes** - Stealth, Balanced, Aggressive  
✅ **Professional documentation** - README, API docs, troubleshooting  
✅ **Easy installation** - Automated setup script  
✅ **Simple usage** - One-command processing  

Sistem siap digunakan! 🚀
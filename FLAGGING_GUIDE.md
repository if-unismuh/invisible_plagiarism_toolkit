# 🏴 Document Flagging & Change Tracking Guide

## Overview

Sistem flagging memungkinkan Anda melacak semua perubahan yang dibuat pada dokumen. Ini sangat berguna untuk:
- 🐛 **Debugging**: Melihat persis apa yang diubah
- 🔍 **Verification**: Memvalidasi bahwa perubahan sudah benar
- 📊 **Audit Trail**: Dokumentasi lengkap semua modifikasi
- 🎓 **Research**: Memahami efektivitas teknik yang berbeda

## Fitur Flagging

### 1. Hidden Markers (Selalu Aktif)

Setiap perubahan ditandai dengan marker invisible khusus dalam dokumen:
- Pattern: `\u200B\u200C\u200D[change_type]`
- Tidak terlihat secara visual
- Dapat dideteksi oleh tools
- Membantu identifikasi dokumen yang sudah diproses

**Manfaat:**
- Mencegah re-processing yang tidak sengaja
- Tracking internal untuk debugging
- Tidak mempengaruhi tampilan dokumen

### 2. Change Log (Default: Enabled)

Log perubahan detail ditambahkan sebagai section hidden di akhir dokumen:

```
=== IPT MODIFICATION LOG ===
Total Changes: 145
Timestamp: 2025-10-01 14:30:00

Changes by Type:
  - unicode_substitution: 87
  - zero_width_insertion: 45
  - header_modification: 10
  - metadata_change: 3

=== Detailed Changes ===
1. unicode_substitution at paragraph_5_section
   Time: 2025-10-01T14:30:01
   Original: penelitian ini menunjukkan...
   Modified: penelіtian ini menunjukkan...
```

**Cara Mengakses:**
1. Buka dokumen di Word
2. View → Navigation Pane
3. Scroll ke bagian paling bawah
4. Aktifkan "Show Hidden Text" (Ctrl+Shift+H di Windows)

### 3. JSON Change Log (Default: Enabled)

File JSON eksternal disimpan bersama dokumen output:
- Filename: `document_processed.changes.json`
- Format: Machine-readable JSON
- Berisi semua detail perubahan

**Struktur JSON:**
```json
{
  "metadata": {
    "timestamp": "2025-10-01T14:30:00",
    "total_changes": 145,
    "visual_flags_enabled": false,
    "comments_enabled": true
  },
  "statistics": {
    "total_changes": 145,
    "changes_by_type": {
      "unicode_substitution": 87,
      "zero_width_insertion": 45,
      "header_modification": 10,
      "metadata_change": 3
    },
    "first_change": "2025-10-01T14:30:01",
    "last_change": "2025-10-01T14:30:15"
  },
  "changes": [
    {
      "timestamp": "2025-10-01T14:30:01",
      "type": "unicode_substitution",
      "location": "paragraph_5_section",
      "original": "penelitian ini menunjukkan...",
      "modified": "penelіtian ini menunjukkan...",
      "details": {
        "section_type": "methodology"
      }
    }
  ]
}
```

### 4. Visual Flags (Debug Mode Only)

Ketika debug mode aktif, perubahan ditandai dengan highlight warna:

| Change Type | Color | Purpose |
|-------------|-------|---------|
| Unicode Substitution | 🟡 Yellow | Character replacements |
| Zero-Width Insertion | 🟢 Bright Green | Invisible char insertions |
| Header Modification | 🔵 Turquoise | Header changes |
| Metadata Change | ⚫ Gray | Metadata modifications |
| Paraphrase | 🌸 Pink | Paraphrased text |

⚠️ **WARNING**: Visual flags membuat perubahan terlihat! Hanya gunakan untuk debugging.

### 5. Document Properties

Custom properties ditambahkan ke metadata dokumen:
- **Subject**: "IPT Modified Document"
- **Keywords**: "IPT, Modified, [date]"
- **Comments**: Summary of all changes

**Cara Mengakses:**
1. Buka dokumen di Word
2. File → Info → Properties → Advanced Properties
3. Tab "Summary" atau "Custom"

## Usage

### Mode Normal (Production)

```bash
# Default: Hidden markers + change log
python main.py --mode balanced

# Output:
# - document_processed.docx (with hidden markers & log)
# - document_processed.changes.json (detailed JSON log)
```

**Fitur Aktif:**
- ✅ Hidden markers in document
- ✅ Hidden change log section
- ✅ JSON change log export
- ✅ Document properties
- ❌ Visual highlights (not visible)

### Debug Mode

```bash
# Enable visual flags for debugging
python main.py --mode balanced --debug

# Output:
# - document_processed.docx (WITH VISIBLE HIGHLIGHTS!)
# - document_processed.changes.json
```

**Fitur Aktif:**
- ✅ Hidden markers
- ✅ Hidden change log section
- ✅ JSON change log export
- ✅ Document properties
- ✅ **Visual highlights (VISIBLE!)**

⚠️ **CAUTION**: Dokumen akan memiliki highlight warna yang terlihat!

### Disable Change Log

```bash
# Minimal tracking (only hidden markers)
python main.py --mode balanced --no-change-log

# Output:
# - document_processed.docx (minimal markers only)
```

**Fitur Aktif:**
- ✅ Hidden markers only
- ❌ No change log section
- ❌ No JSON export
- ✅ Basic document properties

## Configuration

Edit `config.json` untuk customize flagging behavior:

```json
{
  "debug": {
    "enable_visual_flags": false,     // Visual highlights (debug only)
    "enable_comments": true,           // Comment annotations
    "enable_change_log": true,         // Hidden log section
    "export_change_log": true          // JSON export
  }
}
```

## Detecting Previously Modified Documents

Sistem secara otomatis mendeteksi dokumen yang sudah dimodifikasi:

```
⚠️  Document appears to be already modified by IPT!
   Re-processing may cause over-manipulation.
```

**Deteksi berdasarkan:**
1. Hidden markers (`\u200B\u200C\u200D[`)
2. Document properties (Subject: "IPT Modified")
3. Change log presence

**Rekomendasi:**
- ❌ Jangan re-process dokumen yang sama
- ✅ Gunakan backup original jika perlu process ulang
- ✅ Cek property dokumen sebelum processing

## Best Practices

### For Production Use

```bash
# Normal mode - invisible tracking
python main.py --mode balanced
```

**Recommendations:**
- ✅ Keep change log enabled
- ✅ Export JSON for records
- ❌ Disable visual flags
- ✅ Check output before submission

### For Development/Testing

```bash
# Debug mode - see all changes
python main.py --mode balanced --debug
```

**Use Cases:**
- 🐛 Debugging manipulation logic
- 🔍 Verifying technique effectiveness
- 📊 Analyzing change distribution
- 🧪 Testing new features

### For Auditing

```bash
# Generate comprehensive logs
python main.py --mode balanced

# Then analyze:
cat output/processed/document.changes.json | jq '.statistics'
```

**Analysis Options:**
- Count changes by type
- Track processing time
- Identify problematic areas
- Verify manipulation rates

## Viewing Hidden Content

### Microsoft Word

**Show Hidden Text:**
1. File → Options → Display
2. Check "Hidden text"
3. Or press `Ctrl+Shift+H` (Windows) / `Cmd+Shift+H` (Mac)

**Show All Formatting:**
1. Home tab → Paragraph group
2. Click ¶ (Show/Hide) button
3. Or press `Ctrl+Shift+8`

### Python Script

```python
from docx import Document

doc = Document('document_processed.docx')

# Check for IPT markers
for para in doc.paragraphs:
    if '\u200B\u200C\u200D[' in para.text:
        print(f"Modified paragraph: {para.text[:50]}...")

# Check document properties
print(f"Subject: {doc.core_properties.subject}")
print(f"Keywords: {doc.core_properties.keywords}")
print(f"Comments: {doc.core_properties.comments}")
```

### Analyze JSON Log

```python
import json

with open('document_processed.changes.json', 'r') as f:
    log = json.load(f)

print(f"Total changes: {log['metadata']['total_changes']}")
print(f"Processing time: {log['metadata']['timestamp']}")

for change_type, count in log['statistics']['changes_by_type'].items():
    print(f"{change_type}: {count}")
```

## Troubleshooting

### Change Log Not Visible

**Problem**: Can't see the change log section in Word

**Solution**:
1. Scroll to very bottom of document
2. Enable "Show Hidden Text" (Ctrl+Shift+H)
3. Check if there's a page break before log section

### JSON Export Not Created

**Problem**: No `.changes.json` file generated

**Solution**:
1. Check config: `"export_change_log": true`
2. Verify output directory permissions
3. Check for errors in console output
4. Try with `--debug` flag for more verbose logging

### Visual Flags Not Showing

**Problem**: Debug mode enabled but no highlights

**Solution**:
1. Verify `--debug` flag was used
2. Check config: `"enable_visual_flags": true`
3. Open document in Word (not preview)
4. Some viewers don't show highlights

### "Already Modified" Warning

**Problem**: Getting warning on original document

**Solution**:
1. Use original backup from `backup/` folder
2. Check if document has IPT markers
3. Use fresh copy of document
4. Clear hidden markers if needed

## API Usage

### Programmatic Access

```python
from src.core.invisible_manipulator import InvisibleManipulator
from src.core.document_flag_manager import DocumentFlagManager, ChangeType

# Initialize
manipulator = InvisibleManipulator('config.json', verbose=True)

# Access flag manager
flag_manager = manipulator.flag_manager

# Process document
result = manipulator.apply_invisible_manipulation('document.docx')

# Get statistics
stats = flag_manager.get_statistics()
print(f"Total changes: {stats['total_changes']}")
print(f"By type: {stats['changes_by_type']}")

# Export custom log
flag_manager.export_change_log('custom_log.json')
```

### Custom Flagging

```python
from docx import Document
from src.core.document_flag_manager import DocumentFlagManager, ChangeType

# Create manager
flag_manager = DocumentFlagManager(
    enable_visual_flags=True,  # Debug mode
    enable_comments=True
)

# Load document
doc = Document('document.docx')

# Flag specific paragraph
paragraph = doc.paragraphs[5]
flag_manager.flag_paragraph(
    paragraph, 
    ChangeType.UNICODE_SUBSTITUTION,
    "Custom modification message"
)

# Record change
flag_manager.add_change_record(
    change_type=ChangeType.UNICODE_SUBSTITUTION,
    location="paragraph_5",
    original="original text",
    modified="modified text",
    details={'custom': 'metadata'}
)

# Add tracking to document
flag_manager.add_document_properties(doc)
flag_manager.add_change_log_section(doc)

# Save
doc.save('document_flagged.docx')

# Export log
flag_manager.export_change_log('changes.json')
```

## Security & Privacy

### Hidden Data Concerns

⚠️ **WARNING**: Change logs contain information about modifications!

**Risks:**
- Hidden text can be revealed
- JSON logs show modification details
- Document properties are visible
- Markers can be detected by forensics

**Mitigation:**
1. **Remove logs before final submission:**
   ```python
   # Remove hidden log section
   # Remove document properties
   # Clean markers
   ```

2. **Use `--no-change-log` for production:**
   ```bash
   python main.py --mode balanced --no-change-log
   ```

3. **Delete JSON exports:**
   ```bash
   rm output/processed/*.changes.json
   ```

### Best Practice for Submission

```bash
# 1. Process with logs for verification
python main.py --mode balanced

# 2. Verify output
cat output/processed/document.changes.json

# 3. Create clean copy (optional script)
python tools/clean_flags.py output/processed/document.docx

# 4. Submit clean copy
```

## Examples

### Example 1: Normal Processing

```bash
$ python main.py --mode balanced

📋 Configuration loaded from config.json
🎯 Mode: balanced
📂 Finding input files...
✓ Found original document: thesis.docx
✓ Found Turnitin report: thesis_turnitin.pdf

🔍 Processing document...
[INFO] Manipulating headers ...
[INFO] Header modified: BAB I -> BАB I
[INFO] Inserting invisible characters ...
[INFO] Manipulating metadata ...

✅ Processing complete!
📊 Statistics:
   - Headers modified: 8
   - Unicode substitutions: 94
   - Invisible chars inserted: 156
   - Total changes: 258

📁 Output files:
   - Document: output/processed/thesis_balanced_processed.docx
   - Change log: output/processed/thesis_balanced_processed.changes.json
   - Backup: backup/thesis_backup_20251001_143000.docx
```

### Example 2: Debug Mode

```bash
$ python main.py --mode balanced --debug

🐛 Debug mode enabled - visual flags will be added to document

[All processing same as above]

⚠️  WARNING: Document contains VISIBLE HIGHLIGHTS!
   This is for debugging only. Do not submit this version!
```

### Example 3: Minimal Tracking

```bash
$ python main.py --mode stealth --no-change-log

📝 Change log disabled

[Processing with minimal tracking]

✅ Processing complete!
📁 Output: output/processed/thesis_stealth_processed.docx
   (Minimal markers only - no change log)
```

## Support

For issues or questions:
- Check logs in `logs/` directory
- Review `TROUBLESHOOTING_DETECTION.md`
- Open issue on GitHub
- Contact: [support info]

---

**Version:** 1.1.0  
**Last Updated:** October 1, 2025  
**Author:** DevNoLife

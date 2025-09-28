# main.py
"""
Invisible Plagiarism Tool - Main Entry Point
Complete steganographic document manipulation system
Features: Unicode substitution, Invisible characters, Metadata manipulation

Author: DevNoLife  
Version: 1.0 - Production Ready
Usage: python main.py [options]
"""
import os
import sys
import json
import argparse
import traceback
import random
from datetime import datetime
from pathlib import Path

# Import our modules
from invisible_manipulator import InvisibleManipulator
from unicode_steganography import UnicodeSteg, create_invisible_chars_file, create_header_patterns_file

try:
    import docx
except ImportError:
    docx = None


def setup_project_structure():
    """Setup project directory structure"""
    directories = [
        'input',
        'output/processed_documents', 
        'output/analysis_reports',
        'output/comparison_files',
        'backup',
        'data',
        'tools',
        'templates'
    ]
    
    print("📁 Setting up project structure...")
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    # Create data files if they don't exist
    create_essential_files()
    
    print("✅ Project structure ready")


def create_essential_files():
    """Create essential configuration and data files"""
    
    # Create config.json if it doesn't exist
    if not os.path.exists('config.json'):
        create_config_file()
    
    # Create data files
    data_files = [
        'data/unicode_mappings.json',
        'data/invisible_chars.json', 
        'data/header_patterns.json'
    ]
    
    missing_files = [f for f in data_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"📋 Creating {len(missing_files)} missing data files...")
        
        # Initialize Unicode steganography to generate files
        unicode_steg = UnicodeSteg()
        unicode_steg.generate_mapping_file()
        create_invisible_chars_file()
        create_header_patterns_file()


def create_config_file():
    """Create default configuration file"""
    config = {
        "app_info": {
            "name": "Invisible Plagiarism Tool",
            "version": "1.0",
            "created": datetime.now().isoformat()
        },
        "invisible_techniques": {
            "zero_width_chars": {
                "enabled": True,
                "insertion_rate": 0.05,
                "target_locations": ["headers", "after_punctuation", "between_words"],
                "chars": ["\u200B", "\u200C", "\u200D", "\uFEFF"],
                "randomization": True
            },
            "unicode_substitution": {
                "enabled": True,
                "substitution_rate": 0.03,
                "target_chars": ["a", "e", "o", "p", "c", "x", "y"],
                "priority_words": ["BAB", "PENDAHULUAN", "METODE", "HASIL", "KESIMPULAN"],
                "stealth_level": "medium"
            },
            "spacing_manipulation": {
                "enabled": False,
                "micro_adjustments": True,
                "spacing_variance": 0.1
            },
            "metadata_manipulation": {
                "enabled": True,
                "modify_properties": True,
                "add_invisible_content": True
            }
        },
        "detection_targets": {
            "turnitin": {
                "priority": "high",
                "bypass_techniques": ["unicode_substitution", "invisible_chars"],
                "aggressiveness": 0.05
            },
            "copyscape": {
                "priority": "medium",
                "bypass_techniques": ["spacing_manipulation"],
                "aggressiveness": 0.03
            },
            "grammarly": {
                "priority": "low", 
                "bypass_techniques": ["invisible_chars"],
                "aggressiveness": 0.02
            }
        },
        "safety_settings": {
            "preserve_readability": True,
            "maintain_formatting": True,
            "backup_original": True,
            "max_changes_per_paragraph": 5,
            "avoid_obvious_patterns": True,
            "verification_enabled": True
        },
        "processing_modes": {
            "stealth": {
                "description": "Maximum stealth, minimal changes",
                "aggressiveness": 0.02,
                "techniques": ["invisible_chars"]
            },
            "balanced": {
                "description": "Balanced approach",
                "aggressiveness": 0.05,
                "techniques": ["unicode_substitution", "invisible_chars"]
            },
            "aggressive": {
                "description": "Maximum effectiveness",
                "aggressiveness": 0.1,
                "techniques": ["unicode_substitution", "invisible_chars", "metadata_manipulation"]
            }
        }
    }
    
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print("✅ Configuration file created: config.json")


def find_documents(directory="input"):
    """Find all processable documents"""
    supported_formats = ['.docx']
    documents = []
    
    input_path = Path(directory)
    if not input_path.exists():
        return documents
    
    for file_path in input_path.rglob('*'):
        if file_path.suffix.lower() in supported_formats and not file_path.name.startswith('~'):
            documents.append(file_path)
    
    return sorted(documents)


def select_document(auto_select=False):
    """Let user select document or auto-select"""
    documents = find_documents()
    
    if not documents:
        print("❌ No documents found in 'input/' directory")
        print("💡 Please add your .docx files to the 'input/' folder")
        return None
    
    print(f"📄 Found {len(documents)} document(s):")
    print("-" * 50)
    
    for i, doc_path in enumerate(documents, 1):
        file_size = doc_path.stat().st_size / 1024  # KB
        mod_time = datetime.fromtimestamp(doc_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        
        print(f"  {i}. {doc_path.name}")
        print(f"     📂 {doc_path.parent}")
        print(f"     📏 {file_size:.1f} KB | 🕒 {mod_time}")
        print()
    
    if auto_select or len(documents) == 1:
        selected = documents[0]
        print(f"✅ Auto-selected: {selected.name}")
        return selected
    
    # Interactive selection
    while True:
        try:
            choice = input(f"Select document (1-{len(documents)}): ").strip()
            index = int(choice) - 1
            
            if 0 <= index < len(documents):
                return documents[index]
            else:
                print(f"❌ Please enter a number between 1 and {len(documents)}")
        
        except (ValueError, KeyboardInterrupt, EOFError):
            print("❌ Selection cancelled")
            return None


def process_document(input_file, mode='balanced', verify_result=True, verbose=False, dry_run=False, force=False):
    """Process document with invisible manipulation.

    dry_run: simulate only, no output file produced.
    force: override idempotency filename guard.
    """
    print(f"🎯 Processing: {input_file.name}")
    print(f"🔧 Mode: {mode}")
    if dry_run:
        print("🧪 Dry-run mode (no file will be written)")
    if not force and '_invisible_' in input_file.name:
        print("⚠️ Detected already processed filename (contains '_invisible_'). Use --force to override.")
        return None
    
    # Initialize manipulator
    manipulator = InvisibleManipulator(verbose=verbose)

    # Adjust aggressiveness based on mode (scales substitution & insertion rates temporarily)
    mode_scaling = {
        'stealth': 0.5,
        'balanced': 1.0,
        'aggressive': 1.8
    }
    scale = mode_scaling.get(mode, 1.0)
    # Mutate runtime config (not persisted)
    try:
        sub_conf = manipulator.config['invisible_techniques']['unicode_substitution']
        zero_conf = manipulator.config['invisible_techniques']['zero_width_chars']
        sub_conf['effective_substitution_rate'] = sub_conf.get('substitution_rate', 0.03) * scale
        zero_conf['effective_insertion_rate'] = zero_conf.get('insertion_rate', 0.05) * scale
    except Exception:
        pass
    
    # Process the document
    result = manipulator.apply_invisible_manipulation(str(input_file), dry_run=dry_run)
    
    if not result:
        print("❌ Processing failed")
        return None
    
    # Verify result if enabled
    if verify_result and result['backup_file']:
        print("\n🔍 Verifying invisibility...")
        verification = manipulator.verify_invisibility(
            result['backup_file'], 
            result['output_file']
        )
        
        if verification:
            result['verification'] = verification
    
    # Generate comprehensive report
    report = generate_processing_report(result, mode)
    save_processing_report(report)
    
    return result


def generate_processing_report(result, mode):
    """Generate comprehensive processing report"""
    report = {
        'app_info': {
            'name': "Invisible Plagiarism Tool",
            'version': "1.0",
            'processing_timestamp': datetime.now().isoformat(),
            'mode_used': mode
        },
        'file_info': {
            'input_file': str(result['input_file']),
            'output_file': str(result['output_file']),
            'backup_file': result.get('backup_file'),
            'file_size_original': os.path.getsize(result['input_file']) if os.path.exists(result['input_file']) else 0,
            'file_size_processed': os.path.getsize(result['output_file']) if os.path.exists(result['output_file']) else 0
        },
        'processing_stats': result['stats'],
        'verification_results': result.get('verification'),
        'recommendations': []
    }
    
    # Attach seed if exists
    seed_val = globals().get('RANDOM_SEED')
    if seed_val is not None:
        report['app_info']['seed'] = seed_val

    # Add recommendations based on results
    stats = result['stats']
    if stats['headers_modified'] > 0:
        report['recommendations'].append("✅ Headers successfully processed with invisible modifications")
    
    if stats['chars_substituted'] > 0:
        report['recommendations'].append(f"🔤 {stats['chars_substituted']} characters substituted with visually identical Unicode")
    
    if stats['invisible_chars_inserted'] > 0:
        report['recommendations'].append(f"👻 {stats['invisible_chars_inserted']} invisible characters strategically inserted")
    
    # Verification recommendations
    if 'verification' in result:
        verification = result['verification']
        invisibility_ratio = verification['invisible_changes'] / max(1, verification['invisible_changes'] + verification['visible_changes'])
        
        if invisibility_ratio > 0.9:
            report['recommendations'].append("🎯 Excellent invisibility achieved (>90% invisible changes)")
        elif invisibility_ratio > 0.7:
            report['recommendations'].append("✅ Good invisibility achieved (>70% invisible changes)")
        else:
            report['recommendations'].append("⚠️ Some visible changes detected - consider review")
    
    return report


def save_processing_report(report):
    """Save processing report to file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"output/analysis_reports/processing_report_{timestamp}.json"
    
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"📋 Processing report saved: {report_file}")
        return report_file
    
    except Exception as e:
        print(f"⚠️ Could not save report: {e}")
        return None


def print_final_summary(result):
    """Print final processing summary"""
    print("\n" + "=" * 60)
    print("🎉 INVISIBLE MANIPULATION COMPLETED")
    print("=" * 60)
    
    print(f"📄 Input: {Path(result['input_file']).name}")
    if result.get('dry_run'):
        print("📤 Output: (dry-run) no file written")
    else:
        print(f"📤 Output: {Path(result['output_file']).name}")
    
    if result.get('backup_file'):
        print(f"💾 Backup: {Path(result['backup_file']).name}")
    
    stats = result['stats']
    print(f"\n📊 PROCESSING STATISTICS:")
    print(f"   📑 Headers modified: {stats['headers_modified']}")
    print(f"   🔤 Characters substituted: {stats['chars_substituted']}")
    print(f"   👻 Invisible chars inserted: {stats['invisible_chars_inserted']}")
    print(f"   📋 Metadata modifications: {stats['metadata_modified']}")
    print(f"   ⏱️ Processing time: {stats['processing_time']:.2f}s")
    
    # Verification results
    if 'verification' in result:
        verification = result['verification']
        print(f"\n🔍 INVISIBILITY VERIFICATION:")
        print(f"   👻 Invisible changes: {verification['invisible_changes']}")
        print(f"   👁️ Visible changes: {verification['visible_changes']}")
        print(f"   📊 Total char changes: {verification['total_chars_changed']}")
        
        invisibility_ratio = verification['invisible_changes'] / max(1, verification['invisible_changes'] + verification['visible_changes'])
        print(f"   🎯 Invisibility score: {invisibility_ratio:.1%}")
    
    if not result.get('dry_run'):
        print(f"\n📁 OUTPUT LOCATION:")
        print(f"   📂 Folder: {Path(result['output_file']).parent}")
        print(f"   📄 File: {Path(result['output_file']).name}")
    
    print(f"\n💡 NEXT STEPS:")
    print(f"   1. Review the processed document")
    print(f"   2. Check that formatting is preserved")
    print(f"   3. Test with plagiarism detection tools")
    print(f"   4. Keep backup for comparison")
    
    print("=" * 60)


def interactive_mode():
    """Interactive mode for document processing"""
    print("🎮 INTERACTIVE MODE")
    print("Choose your processing options:")
    
    # Select document
    document = select_document()
    if not document:
        return False
    
    # Select processing mode
    modes = ['stealth', 'balanced', 'aggressive']
    print(f"\n🔧 Available processing modes:")
    for i, mode in enumerate(modes, 1):
        print(f"  {i}. {mode.title()}")
    
    try:
        mode_choice = input(f"Select mode (1-3) [default: 2]: ").strip() or '2'
        mode_index = int(mode_choice) - 1
        
        if 0 <= mode_index < len(modes):
            selected_mode = modes[mode_index]
        else:
            selected_mode = 'balanced'
            print(f"Invalid choice, using: {selected_mode}")
        
    except (ValueError, EOFError):
        selected_mode = 'balanced'
        print(f"Using default mode: {selected_mode}")
    
    # Ask about verification
    try:
        verify_choice = input("Enable verification? (y/N): ").strip().lower()
        enable_verification = verify_choice in ['y', 'yes']
    except (EOFError, KeyboardInterrupt):
        enable_verification = True
    
    # Process document
    print(f"\n🚀 Starting processing...")
    result = process_document(document, selected_mode, enable_verification, verbose=False)
    
    if result:
        print_final_summary(result)
        return True
    else:
        print("❌ Processing failed")
        return False


def batch_mode(input_dir="input", mode="balanced"):
    """Batch process all documents in directory"""
    print(f"📦 BATCH MODE - Processing all documents in '{input_dir}'")
    
    documents = find_documents(input_dir)
    
    if not documents:
        print(f"❌ No documents found in '{input_dir}' directory")
        return False
    
    print(f"📄 Found {len(documents)} documents to process")
    
    results = []
    successful = 0
    failed = 0
    
    for i, document in enumerate(documents, 1):
        print(f"\n📄 Processing {i}/{len(documents)}: {document.name}")
        
        try:
            result = process_document(document, mode, verify_result=False)
            
            if result:
                results.append(result)
                successful += 1
                print(f"   ✅ Success")
            else:
                failed += 1
                print(f"   ❌ Failed")
        
        except Exception as e:
            failed += 1
            print(f"   ❌ Error: {e}")
    
    # Print batch summary
    print(f"\n📊 BATCH PROCESSING SUMMARY:")
    print(f"   📄 Total documents: {len(documents)}")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📁 Output directory: output/processed_documents/")
    
    return successful > 0


def create_sample_document():
    """Create sample document for testing"""
    sample_content = """BAB I
PENDAHULUAN

A. Latar Belakang

Perkembangan teknologi informasi yang pesat telah mengubah cara masyarakat dalam berinteraksi dan melakukan transaksi. Salah satu bentuk inovasi yang paling signifikan adalah munculnya platform e-commerce seperti Shopee yang telah mentransformasi lanskap perdagangan retail di Indonesia.

Shopee sebagai marketplace terbesar di Asia Tenggara telah menciptakan ekosistem digital yang memungkinkan jutaan konsumen untuk berbelanja secara online. Platform ini menyediakan berbagai fitur dan layanan yang dirancang untuk meningkatkan pengalaman berbelanja konsumen.

Penelitian ini dilakukan untuk menganalisis pengaruh harga dan kualitas produk terhadap keputusan pembelian online melalui aplikasi Shopee. Berdasarkan data yang diperoleh dari survei konsumen, dapat diketahui bahwa faktor harga dan kualitas produk memiliki pengaruh yang signifikan terhadap keputusan pembelian.

B. Rumusan Masalah

Berdasarkan latar belakang yang telah dipaparkan, maka rumusan masalah dalam penelitian ini adalah:

1. Bagaimana pengaruh harga produk terhadap keputusan pembelian online melalui aplikasi Shopee?
2. Bagaimana pengaruh kualitas produk terhadap keputusan pembelian online melalui aplikasi Shopee?
3. Bagaimana pengaruh harga dan kualitas produk secara simultan terhadap keputusan pembelian online melalui aplikasi Shopee?

C. Tujuan Penelitian

Penelitian ini bertujuan untuk:
1. Menganalisis pengaruh harga produk terhadap keputusan pembelian online melalui aplikasi Shopee
2. Menganalisis pengaruh kualitas produk terhadap keputusan pembelian online melalui aplikasi Shopee
3. Menganalisis pengaruh harga dan kualitas produk secara simultan terhadap keputusan pembelian online melalui aplikasi Shopee

BAB II
TINJAUAN PUSTAKA

A. Landasan Teori

1. E-commerce dan Marketplace
E-commerce atau perdagangan elektronik adalah kegiatan perdagangan yang dilakukan melalui internet. Menurut Kotler dan Keller (2016), e-commerce merupakan saluran pemasaran yang menggunakan teknologi internet untuk menjual produk dan layanan kepada konsumen.

2. Keputusan Pembelian
Keputusan pembelian adalah proses dimana konsumen mengidentifikasi masalah, mencari informasi, mengevaluasi alternatif, melakukan pembelian, dan mengevaluasi hasil pembelian (Kotler & Armstrong, 2018).

3. Harga
Harga adalah jumlah uang yang harus dibayarkan konsumen untuk memperoleh suatu produk atau layanan. Harga merupakan salah satu faktor penting dalam keputusan pembelian konsumen.

4. Kualitas Produk
Kualitas produk adalah kemampuan produk untuk memberikan kinerja yang sesuai atau bahkan melebihi harapan konsumen. Produk berkualitas tinggi akan meningkatkan kepuasan konsumen dan mempengaruhi keputusan pembelian.

BAB III
METODE PENELITIAN

A. Jenis Penelitian
Penelitian ini menggunakan pendekatan kuantitatif dengan metode survei. Data dikumpulkan melalui kuesioner yang disebarkan kepada responden yang merupakan pengguna aplikasi Shopee.

B. Populasi dan Sampel
Populasi dalam penelitian ini adalah seluruh pengguna aplikasi Shopee di Indonesia. Sampel penelitian berjumlah 100 responden yang dipilih menggunakan teknik purposive sampling.

C. Teknik Analisis Data
Data yang telah dikumpulkan dianalisis menggunakan analisis regresi berganda dengan bantuan software SPSS. Analisis ini digunakan untuk mengetahui pengaruh variabel independen terhadap variabel dependen.

BAB IV
HASIL DAN PEMBAHASAN

A. Karakteristik Responden
Berdasarkan hasil survei yang dilakukan, mayoritas responden adalah perempuan (65%) dengan rentang usia 20-30 tahun (70%). Sebagian besar responden memiliki pendidikan terakhir S1 (55%) dan bekerja sebagai karyawan swasta (45%).

B. Analisis Deskriptif
Hasil analisis deskriptif menunjukkan bahwa rata-rata responden memberikan penilaian yang baik terhadap harga produk di Shopee (mean = 4.2), kualitas produk (mean = 4.1), dan keputusan pembelian (mean = 4.3).

C. Analisis Regresi
Hasil analisis regresi berganda menunjukkan bahwa:
1. Harga produk berpengaruh positif dan signifikan terhadap keputusan pembelian (β = 0.35, p < 0.05)
2. Kualitas produk berpengaruh positif dan signifikan terhadap keputusan pembelian (β = 0.42, p < 0.05)
3. Secara simultan, harga dan kualitas produk berpengaruh signifikan terhadap keputusan pembelian (F = 45.6, p < 0.05)

BAB V
KESIMPULAN

A. Kesimpulan
Berdasarkan hasil penelitian yang telah dilakukan, dapat disimpulkan bahwa:
1. Harga produk berpengaruh positif dan signifikan terhadap keputusan pembelian online melalui aplikasi Shopee
2. Kualitas produk berpengaruh positif dan signifikan terhadap keputusan pembelian online melalui aplikasi Shopee
3. Harga dan kualitas produk secara simultan berpengaruh signifikan terhadap keputusan pembelian online melalui aplikasi Shopee

B. Saran
1. Pihak Shopee disarankan untuk mempertahankan strategi penetapan harga yang kompetitif
2. Penjual di platform Shopee disarankan untuk meningkatkan kualitas produk yang ditawarkan
3. Penelitian selanjutnya dapat menggunakan variabel lain seperti promosi dan layanan pelanggan"""

    # Save to input directory
    input_dir = Path("input")
    input_dir.mkdir(exist_ok=True)
    
    try:
        if not docx:
            print("❌ python-docx not installed. Cannot create sample document.")
            return None
            
        doc = docx.Document()
        
        # Split content into paragraphs and add to document
        paragraphs = sample_content.split('\n\n')
        for paragraph_text in paragraphs:
            if paragraph_text.strip():
                paragraph = doc.add_paragraph(paragraph_text.strip())
                
                # Style headers
                if paragraph_text.strip().startswith('BAB '):
                    paragraph.style = 'Heading 1'
                elif paragraph_text.strip() in ['PENDAHULUAN', 'TINJAUAN PUSTAKA', 'METODE PENELITIAN', 'HASIL DAN PEMBAHASAN', 'KESIMPULAN']:
                    paragraph.style = 'Heading 2'
                elif paragraph_text.strip().startswith(('A. ', 'B. ', 'C. ', '1. ', '2. ', '3. ')):
                    paragraph.style = 'Heading 3'
        
        sample_file = input_dir / "sample_thesis.docx"
        doc.save(str(sample_file))
        
        print(f"✅ Sample document created: {sample_file}")
        return sample_file
        
    except ImportError:
        print("❌ python-docx not installed. Cannot create sample document.")
        return None
    except Exception as e:
        print(f"❌ Error creating sample document: {e}")
        return None


def create_requirements_file():
    """Create requirements.txt file"""
    requirements = """python-docx>=0.8.11
python-docx2txt>=0.8
pathlib
argparse
json
datetime
shutil
unicodedata
random
re
os
sys
"""
    
    with open('requirements.txt', 'w') as f:
        f.write(requirements.strip())
    
    print("✅ Requirements file created: requirements.txt")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Invisible Plagiarism Tool - Steganographic Document Manipulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                           # Interactive mode
  python main.py --batch                   # Batch process all files in input/
  python main.py --file input/thesis.docx  # Process specific file
  python main.py --mode aggressive         # Use aggressive processing
  python main.py --create-sample           # Create sample document
        """
    )
    
    parser.add_argument('--file', '-f', 
                       help='Specific file to process')
    
    parser.add_argument('--mode', '-m', 
                       choices=['stealth', 'balanced', 'aggressive'],
                       default='balanced',
                       help='Processing mode (default: balanced)')
    
    parser.add_argument('--batch', '-b', 
                       action='store_true',
                       help='Batch process all files in input directory')
    
    parser.add_argument('--input-dir', 
                       default='input',
                       help='Input directory for batch processing (default: input)')
    
    parser.add_argument('--no-verify', 
                       action='store_true',
                       help='Disable verification of results')
    
    parser.add_argument('--create-sample', 
                       action='store_true',
                       help='Create sample document for testing')
    
    parser.add_argument('--setup', 
                       action='store_true',
                       help='Setup project structure and files')
    
    parser.add_argument('--version', '-v', 
                       action='store_true',
                       help='Show version information')
    parser.add_argument('--verbose', 
                       action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--seed', type=int, help='Set random seed for reproducible results')
    parser.add_argument('--dry-run', action='store_true', help='Simulate processing without writing output file')
    parser.add_argument('--force', action='store_true', help='Force processing even if file seems already processed')
    
    return parser.parse_args()


def main():
    """Main function"""
    args = parse_arguments()
    
    # Handle simple commands first
    if args.version:
        print("Invisible Plagiarism Tool v1.0")
        print("Advanced Steganographic Document Manipulation")
        return
    
    # Initialize app
    print("🔮 Invisible Plagiarism Tool v1.0")
    print("✨ Advanced Steganographic Document Manipulation")
    print("=" * 60)
    if getattr(args, 'seed', None) is not None:
        random.seed(args.seed)
        globals()['RANDOM_SEED'] = args.seed
        print(f"[SEED] Using random seed: {args.seed}")
    
    if args.setup:
        setup_project_structure()
        print("✅ Project setup completed")
        create_requirements_file()
        return
    
    if args.create_sample:
        sample_file = create_sample_document()
        if sample_file:
            print(f"💡 Use: python main.py --file {sample_file}")
        return

    # Main processing modes
    try:
        if args.batch:
            # Batch processing mode
            if args.verbose:
                print("[INFO] Verbose logging enabled")
            success = batch_mode(args.input_dir, args.mode)
            if not success:
                sys.exit(1)
        
        elif args.file:
            # Single file processing mode
            input_file = Path(args.file)
            
            if not input_file.exists():
                print(f"❌ File not found: {input_file}")
                sys.exit(1)
            
            verify = not args.no_verify
            result = process_document(input_file, args.mode, verify, verbose=args.verbose, dry_run=args.dry_run, force=args.force)
            
            if result:
                print_final_summary(result)
            else:
                print("❌ Processing failed")
                sys.exit(1)
        
        else:
            # Interactive mode (default)
            success = interactive_mode()
            if not success:
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Processing interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Asset Register ISO 55000 Specialist - Main Orchestrator
Coordinates all tools to provide comprehensive asset management intelligence.
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

# Python 3.13 handles UTF-8 natively on Windows, no wrapper needed

from drive_reader import DriveReader
from iso_pdf_parser import ISOPDFParser
from asset_data_indexer import AssetDataIndexer
from gemini_query_engine import GeminiQueryEngine
from question_suggester import QuestionSuggester
from command_parser import CommandParser
from asset_updater import AssetUpdater


class AssetSpecialistOrchestrator:
    """Main orchestrator for Asset Register ISO 55000 Specialist."""

    def __init__(self):
        """Initialize orchestrator."""
        load_dotenv()
        self.folder_id = os.getenv('ASSET_REGISTER_FOLDER_ID')
        self.data_dir = 'data/.tmp'

        # File paths
        self.combined_data_file = os.path.join(self.data_dir, 'asset_registers_combined.json')
        self.asset_index_file = os.path.join(self.data_dir, 'asset_index.json')
        self.iso_kb_file = os.path.join(self.data_dir, 'iso_knowledge_base.json')

    def setup(self):
        """
        Complete setup: Fetch data, parse ISO, index assets.
        Run this once to initialize the system.
        """
        print("\n" + "="*70)
        print("=== ASSET REGISTER ISO 55000 SPECIALIST - SETUP ===")
        print("="*70 + "\n")

        # Step 1: Fetch asset registers from Google Drive
        print("STEP 1: Fetching Asset Registers from Google Drive")
        print("-" * 70)
        try:
            reader = DriveReader()
            reader.fetch_all_asset_registers(
                folder_id=self.folder_id,
                output_file=self.combined_data_file
            )
        except Exception as e:
            print(f"\n[ERROR] Failed to fetch asset registers: {e}")
            return False

        # Step 2: Parse ISO 55000 PDFs
        print("\n" + "="*70)
        print("STEP 2: Parsing ISO 55000 Standard Documents")
        print("-" * 70)
        try:
            pdf_files = [
                {'path': os.path.join(self.data_dir, 'ASISO55000-20241.pdf'), 'standard': 'ISO 55000'},
                {'path': os.path.join(self.data_dir, 'ASISO55001-20241.pdf'), 'standard': 'ISO 55001'},
                {'path': os.path.join(self.data_dir, 'ASISO55002-20241.pdf'), 'standard': 'ISO 55002'}
            ]

            parser = ISOPDFParser()
            parser.create_knowledge_base(
                pdf_files=pdf_files,
                output_file=self.iso_kb_file
            )
        except Exception as e:
            print(f"\n[ERROR] Failed to parse ISO PDFs: {e}")
            print("   Note: This is optional - system will work without ISO knowledge base")

        # Step 3: Index asset data
        print("\n" + "="*70)
        print("STEP 3: Indexing Asset Data")
        print("-" * 70)
        try:
            indexer = AssetDataIndexer()
            indexer.process_and_index(
                input_file=self.combined_data_file,
                output_file=self.asset_index_file
            )
        except Exception as e:
            print(f"\n[ERROR] Failed to index assets: {e}")
            return False

        # Setup complete
        print("\n" + "="*70)
        print("[OK] SETUP COMPLETE!")
        print("="*70)
        print("\nYou can now:")
        print("  1. Query the system: python run_asset_specialist.py --query \"your question\"")
        print("  2. Interactive mode: python run_asset_specialist.py --interactive")
        print("  3. Get suggestions: python run_asset_specialist.py --suggest")
        print("="*70 + "\n")

        return True

    def query(self, question: str):
        """
        Process a single query.

        Args:
            question: User question
        """
        if not os.path.exists(self.asset_index_file):
            print("[ERROR] Asset index not found. Please run setup first:")
            print("  python run_asset_specialist.py --setup")
            return

        try:
            engine = GeminiQueryEngine()
            result = engine.query(
                question=question,
                asset_index_file=self.asset_index_file,
                iso_kb_file=self.iso_kb_file if os.path.exists(self.iso_kb_file) else None
            )

            if result['status'] == 'success':
                print("\n" + "="*70)
                print("ANSWER")
                print("="*70)
                print(result['answer'])
                print("="*70)
                print(f"\nModel: {result['model']}")
                print(f"Context Size: {result['context_size']:,} characters")
                print("="*70 + "\n")
            else:
                print(f"\n[ERROR] Query failed: {result.get('error')}")

        except Exception as e:
            print(f"\n[ERROR] Error: {e}")
            import traceback
            traceback.print_exc()

    def interactive(self):
        """Start interactive query session with CRUD support."""
        if not os.path.exists(self.asset_index_file):
            print("[ERROR] Asset index not found. Please run setup first:")
            print("  python run_asset_specialist.py --setup")
            return

        try:
            # Show welcome message with suggestions
            self._show_welcome()

            # Initialize components
            engine = GeminiQueryEngine()
            parser = CommandParser()
            updater = AssetUpdater()

            print("\nStarting interactive session...")
            print("Type 'suggest' for question ideas, 'exit' to quit")
            print("You can also UPDATE, ADD, or DELETE assets through natural language!\n")

            while True:
                try:
                    question = input("Your question: ").strip()

                    if not question:
                        continue

                    if question.lower() in ['exit', 'quit', 'q']:
                        print("\n👋 Goodbye!")
                        break

                    if question.lower() in ['suggest', 'suggestions', 'help']:
                        self.suggest_questions(num=5)
                        continue

                    # Detect command intent
                    intent, params = parser.detect_intent(question)

                    if intent == 'UPDATE':
                        self._handle_update(updater, params)
                    elif intent == 'CREATE':
                        self._handle_create(updater, params)
                    elif intent == 'DELETE':
                        self._handle_delete(updater, params)
                    else:
                        # Process as READ query
                        result = engine.query(
                            question=question,
                            asset_index_file=self.asset_index_file,
                            iso_kb_file=self.iso_kb_file if os.path.exists(self.iso_kb_file) else None
                        )

                        if result['status'] == 'success':
                            print("\n" + "="*70)
                            print("ANSWER")
                            print("="*70)
                            print(result['answer'])
                            print("="*70 + "\n")
                        else:
                            print(f"\n[ERROR] Error: {result.get('error')}\n")

                except KeyboardInterrupt:
                    print("\n\n👋 Goodbye!")
                    break
                except Exception as e:
                    print(f"\n[ERROR] Error: {e}\n")

        except Exception as e:
            print(f"\n[ERROR] Failed to start interactive mode: {e}")
            import traceback
            traceback.print_exc()

    def _handle_update(self, updater, params):
        """Handle UPDATE command."""
        if params['type'] == 'single':
            print(f"\n[WARNING]  Update Asset {params['asset_id']}")
            print(f"    Field: {params['field']}")
            print(f"    New Value: {params['value']}")
            confirm = input("\n    Proceed? (yes/no): ")

            if confirm.lower() == 'yes':
                updater.update_asset(
                    asset_id=params['asset_id'],
                    field=params['field'],
                    new_value=params['value'],
                    confirm=False
                )
                print("\n[OK] Update command sent (Note: Full Google Sheets integration requires setup)")
            else:
                print("\n[ERROR] Update cancelled")

        elif params['type'] == 'bulk':
            print(f"\n[WARNING]  Bulk Update")
            print(f"    Filter: {params['filter_field']} = {params['filter_value']}")
            print(f"    New Value: {params['new_value']}")
            confirm = input("\n    This may affect multiple assets. Proceed? (yes/no): ")

            if confirm.lower() == 'yes':
                updater.bulk_update_by_criteria(
                    filter_field=params['filter_field'],
                    filter_value=params['filter_value'],
                    update_field=params.get('filter_field', 'Condition'),
                    new_value=params['new_value'],
                    confirm=False
                )
                print("\n[OK] Bulk update command sent (Note: Full Google Sheets integration requires setup)")
            else:
                print("\n[ERROR] Bulk update cancelled")

    def _handle_create(self, updater, params):
        """Handle CREATE command."""
        print(f"\n[OK] Create New Asset")
        print(f"    Data: {params['asset_data']}")
        confirm = input("\n    Proceed? (yes/no): ")

        if confirm.lower() == 'yes':
            print("\n[OK] Create command sent (Note: Full implementation requires additional setup)")
            print(f"    New asset would be created with: {params['asset_data']}")
        else:
            print("\n[ERROR] Create cancelled")

    def _handle_delete(self, updater, params):
        """Handle DELETE command."""
        if params['type'] == 'single':
            print(f"\n[WARNING]  WARNING: Delete Asset {params['asset_id']}")
            confirm = input("\n    This cannot be easily undone. Are you sure? (yes/no): ")

            if confirm.lower() == 'yes':
                print("\n[OK] Delete command sent (Note: Full implementation requires additional setup)")
                print(f"    Asset {params['asset_id']} would be deleted")
            else:
                print("\n[ERROR] Delete cancelled")

        elif params['type'] == 'bulk':
            print(f"\n[WARNING]  WARNING: Bulk Delete")
            print(f"    Filter: {params['filter_field']} = {params['filter_value']}")
            confirm = input("\n    This may delete multiple assets. Are you ABSOLUTELY sure? (yes/no): ")

            if confirm.lower() == 'yes':
                print("\n[ERROR] Bulk delete not yet implemented for safety reasons")
            else:
                print("\n[ERROR] Bulk delete cancelled")

    def suggest_questions(self, num: int = 10, difficulty: str = "all"):
        """
        Show question suggestions.

        Args:
            num: Number of suggestions
            difficulty: Difficulty level
        """
        if not os.path.exists(self.asset_index_file):
            print("[ERROR] Asset index not found. Please run setup first:")
            print("  python run_asset_specialist.py --setup")
            return

        try:
            suggester = QuestionSuggester()
            suggestions = suggester.suggest_questions(
                asset_index_file=self.asset_index_file,
                num_suggestions=num,
                difficulty=difficulty
            )

            suggester.display_suggestions(suggestions)

        except Exception as e:
            print(f"\n[ERROR] Error: {e}")
            import traceback
            traceback.print_exc()

    def _show_welcome(self):
        """Show welcome message."""
        print("\n" + "="*70)
        print("=== ASSET REGISTER ISO 55000 SPECIALIST ===")
        print("="*70)
        print("\nWelcome! I'm your AI assistant with expertise in ISO 55000 asset")
        print("management standards. I can help you understand and analyze your")
        print("asset registers.")
        print("\n" + "="*70)

        # Show quick stats
        try:
            import json
            with open(self.asset_index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
                stats = index.get('statistics', {})

            print("\nYOUR ASSET REGISTER:")
            print(f"  • Total Assets: {stats.get('total_assets', 'Unknown')}")
            print(f"  • Total Fields: {stats.get('total_fields', 'Unknown')}")

            sources = stats.get('source_distribution', {})
            if sources:
                print(f"  • Source Files: {len(sources)}")

            print("="*70)

        except:
            pass


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Asset Register ISO 55000 Specialist',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initial setup (run once)
  python run_asset_specialist.py --setup

  # Ask a question
  python run_asset_specialist.py --query "How many assets do we have?"

  # Interactive mode
  python run_asset_specialist.py --interactive

  # Get question suggestions
  python run_asset_specialist.py --suggest

  # Beginner suggestions only
  python run_asset_specialist.py --suggest --difficulty beginner
        """
    )

    parser.add_argument('--setup', action='store_true',
                       help='Run initial setup: fetch data, parse ISO, index assets')
    parser.add_argument('--query', '-q',
                       help='Ask a single question')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Start interactive query session')
    parser.add_argument('--suggest', action='store_true',
                       help='Show question suggestions')
    parser.add_argument('--num', type=int, default=10,
                       help='Number of suggestions (default: 10)')
    parser.add_argument('--difficulty', choices=['beginner', 'advanced', 'all'], default='all',
                       help='Suggestion difficulty level')

    args = parser.parse_args()

    # Create orchestrator
    orchestrator = AssetSpecialistOrchestrator()

    # Execute command
    if args.setup:
        orchestrator.setup()

    elif args.query:
        orchestrator.query(args.query)

    elif args.interactive:
        orchestrator.interactive()

    elif args.suggest:
        orchestrator.suggest_questions(num=args.num, difficulty=args.difficulty)

    else:
        # No command specified - show help
        parser.print_help()
        print("\n💡 TIP: Start with --setup if this is your first time!")


if __name__ == '__main__':
    main()

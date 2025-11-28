import os
import sys
import asyncio
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
from pythonragbase import process_pdf, process_question, create_rag_system

class TestRAGSystem:
    
    def setup_method(self):
        self.test_pdf_path = self.create_test_pdf()
        self.rag_system = create_rag_system()
    
    def teardown_method(self):
        if hasattr(self, 'test_pdf_path') and os.path.exists(self.test_pdf_path):
            os.unlink(self.test_pdf_path)
    
    def create_test_pdf(self):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            
            temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            temp_pdf.close()
            
            c = canvas.Canvas(temp_pdf.name, pagesize=A4)
            c.setFont("Helvetica", 12)
        
            content = [
                "Test Document for RAG System",
                "Subject: Artificial Intelligence and Machine Learning",
                "",
                "Artificial Intelligence (AI) is a branch of computer science dealing with",
                "the creation of intelligent machines that work and react like humans.",
                "",
                "Machine Learning (ML) is a subset of AI that allows computers to learn",
                "from data without being explicitly programmed.",
                "",
                "Key Applications:",
                "1. Natural Language Processing",
                "2. Computer Vision",
                "3. Recommendation Systems",
                "4. Speech Recognition",
                "",
                "Conclusion: AI is transforming various industries and has significant impact."
            ]
            
            y_position = 750
            for line in content:
                c.drawString(50, y_position, line)
                y_position -= 20
                if y_position < 50:
                    c.showPage()
                    y_position = 750
                    c.setFont("Helvetica", 12)
            
            c.save()
            return temp_pdf.name
            
        except ImportError:
            existing_pdf = os.path.join(current_dir, "documents", "AEG_BII.pdf")
            if os.path.exists(existing_pdf):
                return existing_pdf
            else:
                temp_txt = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
                with open(temp_txt.name, 'w', encoding='utf-8') as f:
                    f.write("This is a test document content for RAG system testing.")
                return temp_txt.name

    def test_1_process_pdf_invalid_path(self):
        print("\n🔍 Testing invalid PDF path...")
        try:
            process_pdf("invalid_path/nonexistent.pdf")
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            print("✅ Correctly raised FileNotFoundError for invalid path")
            assert True
        except Exception as e:
            assert False, f"Unexpected error: {e}"

    def test_2_process_pdf_empty_path(self):
        print("\n🔍 Testing empty PDF path...")
        try:
            process_pdf("")
            assert False, "Should have raised ValueError"
        except ValueError:
            print("✅ Correctly raised ValueError for empty path")
            assert True
        except Exception as e:
            assert False, f"Unexpected error: {e}"

    def test_3_process_pdf_wrong_extension(self):
        print("\n🔍 Testing wrong file extension...")
        temp_file = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
        temp_file.write(b"Test content")
        temp_file.close()
        try:
            process_pdf(temp_file.name)
            assert False, "Should have raised ValueError"
        except ValueError:
            print("✅ Correctly raised ValueError for wrong file extension")
            assert True
            os.unlink(temp_file.name)
        except Exception as e:
            os.unlink(temp_file.name)
            assert False, f"Unexpected error: {e}"

    def test_4_process_pdf_valid(self):
        print("\n🔍 Testing valid PDF processing...")
        try:
            chain = process_pdf(self.test_pdf_path)
            assert chain is not None, "Chain should not be None"
            print("✅ PDF processed successfully")
            assert True
        except Exception as e:
            assert False, f"Error processing valid PDF: {e}"

    def test_5_process_question_invalid(self):
        print("\n🔍 Testing invalid question input...")
        chain = process_pdf(self.test_pdf_path)
        try:
            process_question("", chain)
            assert False, "Should have raised ValueError for empty question"
        except ValueError:
            print("✅ Correctly raised ValueError for empty question")
            assert True
        except Exception as e:
            assert False, f"Unexpected error: {e}"
        try:
            process_question("a", chain)
            assert False, "Should have raised ValueError for short question"
        except ValueError:
            print("✅ Correctly raised ValueError for short question")
            assert True
        except Exception as e:
            assert False, f"Unexpected error: {e}"

    def test_6_process_question_valid(self):
        print("\n🔍 Testing valid question processing...")
        try:
            chain = process_pdf(self.test_pdf_path)
            result = process_question("What is this document about?", chain)
            
            assert isinstance(result, dict), "Result should be a dictionary"
            assert "answer" in result, "Result should contain 'answer' key"
            assert "sources" in result, "Result should contain 'sources' key"
            assert isinstance(result["answer"], str), "Answer should be a string"
            assert isinstance(result["sources"], list), "Sources should be a list"
            
            print("✅ Question processed successfully")
            print(f"   Answer length: {len(result['answer'])}")
            print(f"   Sources count: {len(result['sources'])}")
            assert True
            
        except Exception as e:
            assert False, f"Error processing question: {e}"

    def test_7_rag_system_integration(self):
        print("\n🔍 Testing RAG system integration...")
        try:
            self.rag_system.load_pdf(self.test_pdf_path)
            assert self.rag_system.is_loaded, "RAG system should be loaded"
            assert self.rag_system.chain is not None, "Chain should not be None"
            print("✅ PDF loaded successfully in RAG system")
            result = self.rag_system.ask_question("What is the main topic?")
            assert isinstance(result, dict), "Result should be a dictionary"
            assert "answer" in result, "Result should contain answer"
            print("✅ Question answered successfully in RAG system")
            assert True
            
        except Exception as e:
            assert False, f"Error in RAG system integration: {e}"

    def test_8_rag_system_question_before_load(self):
        print("\n🔍 Testing question before PDF load...")
        rag = create_rag_system()
        
        try:
            rag.ask_question("Some question?")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            print("✅ Correctly raised ValueError for question before load")
            assert "load a PDF first" in str(e)
            assert True
        except Exception as e:
            assert False, f"Unexpected error: {e}"

    def test_9_multiple_questions(self):
        print("\n🔍 Testing multiple questions...")
        try:
            self.rag_system.load_pdf(self.test_pdf_path)
            
            questions = [
                "What is AI?",
                "What are the applications?",
                "What is the conclusion?"
            ]
            
            for i, question in enumerate(questions, 1):
                result = self.rag_system.ask_question(question)
                assert result["answer"] is not None, f"Answer should not be None for question {i}"
                print(f"✅ Question {i} answered: {len(result['answer'])} chars")
                print(f"✅ Question {i} Answer : {result["answer"]}")
            
            print("✅ All multiple questions processed successfully")
            assert True
            
        except Exception as e:
            assert False, f"Error in multiple questions test: {e}"

def run_all_tests():
    print("🚀 Starting RAG System Tests...")
    print("=" * 50)
    
    test_suite = TestRAGSystem()
    test_methods = [method for method in dir(test_suite) 
                   if method.startswith('test_') and callable(getattr(test_suite, method))]
    
    passed = 0
    failed = 0
    
    for method_name in test_methods:
        test_suite.setup_method()
        try:
            method = getattr(test_suite, method_name)
            method()
            passed += 1
            print(f"✅ {method_name} - PASSED")
        except AssertionError as e:
            failed += 1
            print(f"❌ {method_name} - FAILED: {e}")
        except Exception as e:
            failed += 1
            print(f"💥 {method_name} - ERROR: {e}")
        finally:
            test_suite.teardown_method()
        print("-" * 40)
    
    print("=" * 50)
    print(f"📊 TEST SUMMARY:")
    print(f"   Total Tests: {len(test_methods)}")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📈 Success Rate: {(passed/len(test_methods))*100:.1f}%")
    
    if failed == 0:
        print("🎉 All tests passed successfully!")
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
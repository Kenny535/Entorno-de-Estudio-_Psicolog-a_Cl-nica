#!/usr/bin/env python3
"""
Simple test to verify COM automation works in this environment
"""
import sys
import traceback

def test_word_com():
    """Test Word COM automation"""
    print("Testing Word COM automation...")
    try:
        import win32com.client
        import pythoncom

        # Initialize COM
        print("  Calling CoInitialize...")
        pythoncom.CoInitialize()
        print("  CoInitialize succeeded")

        # Create Word instance
        print("  Creating Word.Application object...")
        word = win32com.client.Dispatch("Word.Application")
        print("  Word.Application object created successfully")

        # Try to set visibility
        print("  Setting Visible = False...")
        word.Visible = False
        print("  Visible = False succeeded")

        # Create a document
        print("  Creating new document...")
        doc = word.Documents.Add()
        print("  Document created successfully")

        # Add some text
        print("  Adding text to document...")
        doc.Range(0, 0).InsertAfter("Test de automatización COM\n")
        print("  Text added successfully")

        # Save and close
        print("  Saving and closing document...")
        doc.SaveAs(r"C:\temp\test_com_word.docx")
        doc.Close()
        print("  Document saved and closed")

        # Quit Word
        print("  Quitting Word application...")
        word.Quit()
        print("  Word application quit successfully")

        # Uninitialize COM
        print("  Calling CoUninitialize...")
        pythoncom.CoUninitialize()
        print("  CoUninitialize succeeded")

        print("✅ Word COM test PASSED")
        return True

    except Exception as e:
        print(f"❌ Word COM test FAILED: {e}")
        traceback.print_exc()
        try:
            pythoncom.CoUninitialize()
        except:
            pass
        return False

def test_powerpoint_com():
    """Test PowerPoint COM automation"""
    print("\nTesting PowerPoint COM automation...")
    try:
        import win32com.client
        import pythoncom

        # Initialize COM
        print("  Calling CoInitialize...")
        pythoncom.CoInitialize()
        print("  CoInitialize succeeded")

        # Create PowerPoint instance
        print("  Creating PowerPoint.Application object...")
        powerpoint = win32com.client.Dispatch("PowerPoint.Application")
        print("  PowerPoint.Application object created successfully")

        # Try to set visibility
        print("  Setting Visible = False...")
        powerpoint.Visible = False
        print("  Visible = False succeeded")

        # Create a presentation
        print("  Creating new presentation...")
        presentation = powerpoint.Presentations.Add()
        print("  Presentation created successfully")

        # Add a slide
        print("  Adding slide...")
        slide = presentation.Slides.Add(1, 1)  # ppLayoutTitle
        print("  Slide added successfully")

        # Add title text
        print("  Adding title text...")
        slide.Shapes.Title.TextFrame.TextRange.Text = "Test de automatización COM"
        print("  Title text added successfully")

        # Save and close
        print("  Saving and closing presentation...")
        presentation.SaveAs(r"C:\temp\test_com_powerpoint.pptx")
        presentation.Close()
        print("  Presentation saved and closed")

        # Quit PowerPoint
        print("  Quitting PowerPoint application...")
        powerpoint.Quit()
        print("  PowerPoint application quit successfully")

        # Uninitialize COM
        print("  Calling CoUninitialize...")
        pythoncom.CoUninitialize()
        print("  CoUninitialize succeeded")

        print("✅ PowerPoint COM test PASSED")
        return True

    except Exception as e:
        print(f"❌ PowerPoint COM test FAILED: {e}")
        traceback.print_exc()
        try:
            pythoncom.CoUninitialize()
        except:
            pass
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("TESTING COM AUTOMATION")
    print("=" * 50)

    word_success = test_word_com()
    ppt_success = test_powerpoint_com()

    print("\n" + "=" * 50)
    print("RESULTS:")
    print(f"  Word COM: {'✅ PASS' if word_success else '❌ FAIL'}")
    print(f"  PowerPoint COM: {'✅ PASS' if ppt_success else '❌ FAIL'}")
    print("=" * 50)

    if word_success and ppt_success:
        print("🎉 ALL TESTS PASSED - COM automation works correctly!")
        sys.exit(0)
    else:
        print("💥 SOME TESTS FAILED - COM automation has issues")
        sys.exit(1)
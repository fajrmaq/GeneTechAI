"""
test_schemdraw.py - Test if SchemDraw can generate images
"""

import os
import sys

def test_basic_drawing():
    """Test basic drawing with SchemDraw"""
    try:
        print("Testing SchemDraw...")
        
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
        import SchemDraw as schem
        import SchemDraw.elements as e
        
        # Create a simple drawing
        d = schem.Drawing(unit=0.5)
        d.add(e.LINE, d='right', l=2, label='Test')
        d.add(e.DOT)
        
        # Save to file
        os.makedirs('user_files', exist_ok=True)
        d.save('user_files/test_schemdraw.png')
        
        if os.path.exists('user_files/test_schemdraw.png'):
            print("✅ SchemDraw test passed - image created")
            return True
        else:
            print("❌ SchemDraw test failed - no image created")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_matplotlib():
    """Test matplotlib directly"""
    try:
        print("\nTesting matplotlib...")
        import matplotlib.pyplot as plt
        
        plt.figure()
        plt.plot([1, 2, 3], [1, 4, 9])
        plt.title('Test Plot')
        
        os.makedirs('user_files', exist_ok=True)
        plt.savefig('user_files/test_matplotlib.png')
        plt.close()
        
        if os.path.exists('user_files/test_matplotlib.png'):
            print("✅ matplotlib test passed")
            return True
        else:
            print("❌ matplotlib test failed")
            return False
            
    except Exception as e:
        print(f"❌ matplotlib error: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("Testing Image Generation")
    print("="*60)
    
    # Check if user_files exists
    if not os.path.exists('user_files'):
        os.makedirs('user_files')
        print("📁 Created user_files directory")
    
    # Run tests
    schemdraw_ok = test_basic_drawing()
    matplotlib_ok = test_matplotlib()
    
    print("\n" + "="*60)
    print("Results:")
    print(f"SchemDraw: {'✅' if schemdraw_ok else '❌'}")
    print(f"Matplotlib: {'✅' if matplotlib_ok else '❌'}")
    
    if not schemdraw_ok or not matplotlib_ok:
        print("\n🔧 Fix needed!")
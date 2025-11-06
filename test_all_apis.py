#!/usr/bin/env python3
"""
Test všech API endpointů Virtual Fitting Room
"""
import requests
import json
from PIL import Image
import io

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5001"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def test_backend_health():
    print_section("TEST: Backend /health")
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=5)
        print(f"✅ Status: {r.status_code}")
        print(f"Response: {json.dumps(r.json(), indent=2)}")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_backend_root():
    print_section("TEST: Backend /")
    try:
        r = requests.get(f"{BACKEND_URL}/", timeout=5)
        print(f"✅ Status: {r.status_code}")
        data = r.json()
        print(f"Service: {data['service']}")
        print(f"Version: {data['version']}")
        print(f"Device: {data['platform']['device']} ({data['platform']['device_name']})")
        print(f"Models loaded: try_on={data['models']['try_on']}, ollama={data['models']['ollama']}")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_frontend_health():
    print_section("TEST: Frontend /health")
    try:
        r = requests.get(f"{FRONTEND_URL}/health", timeout=5)
        print(f"✅ Status: {r.status_code}")
        print(f"Response: {json.dumps(r.json(), indent=2)}")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_frontend_variants():
    print_section("TEST: Frontend /api/variants")
    try:
        r = requests.get(f"{FRONTEND_URL}/api/variants", timeout=5)
        print(f"✅ Status: {r.status_code}")
        variants = r.json()
        for v in variants:
            print(f"  - {v['display_name']}: ${v['cost_per_generation']:.2f}, avg={v['avg_time']:.1f}s, blacklisted={v['is_blacklisted']}")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_frontend_generations():
    print_section("TEST: Frontend /api/generations")
    try:
        r = requests.get(f"{FRONTEND_URL}/api/generations", timeout=5)
        print(f"✅ Status: {r.status_code}")
        gens = r.json()
        print(f"Total generations: {len(gens)}")
        if gens:
            latest = gens[0]
            print(f"Latest: {latest['person_name']} + {latest['garment_name']}")
            print(f"  Created: {latest['created_at']}")
            print(f"  Status: {latest['status']}")
            print(f"  Rating: {latest['rating']}/5")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_backend_tryon():
    print_section("TEST: Backend /api/tryon (s testovacími obrázky)")
    try:
        # Create test images
        print("Creating test images...")
        person_img = Image.new('RGB', (512, 512), color='red')
        garment_img = Image.new('RGB', (512, 512), color='blue')

        person_bytes = io.BytesIO()
        garment_bytes = io.BytesIO()
        person_img.save(person_bytes, 'JPEG')
        garment_img.save(garment_bytes, 'JPEG')
        person_bytes.seek(0)
        garment_bytes.seek(0)

        files = {
            'person_image': ('person.jpg', person_bytes, 'image/jpeg'),
            'garment_image': ('garment.jpg', garment_bytes, 'image/jpeg')
        }

        print("Calling backend API...")
        r = requests.post(
            f"{BACKEND_URL}/api/tryon",
            files=files,
            params={'use_ollama': False},
            timeout=120
        )

        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            result = r.json()
            print(f"✅ Success!")
            print(f"  Result URL: {result['result_url']}")
            print(f"  Has garment analysis: {result.get('garment_analysis') is not None}")
            return True
        else:
            print(f"❌ Error: {r.text}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("  🧪 VIRTUAL FITTING ROOM - API TEST SUITE")
    print("="*60)

    results = {}

    # Test all endpoints
    results['backend_health'] = test_backend_health()
    results['backend_root'] = test_backend_root()
    results['frontend_health'] = test_frontend_health()
    results['frontend_variants'] = test_frontend_variants()
    results['frontend_generations'] = test_frontend_generations()
    results['backend_tryon'] = test_backend_tryon()

    # Summary
    print_section("📊 TEST SUMMARY")
    passed = sum(results.values())
    total = len(results)

    for test, result in results.items():
        icon = "✅" if result else "❌"
        print(f"  {icon} {test}")

    print(f"\nTotal: {passed}/{total} passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {total - passed} tests failed")

    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

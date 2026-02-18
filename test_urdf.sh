#!/bin/bash
# Quick URDF validation script

echo "=== Testing URDF/Xacro Processing ==="
URDF_FILE="/mnt/nova_ssd/rosmowercompleate/src/rosmower/description/rosmower.urdf.xacro"

if [ ! -f "$URDF_FILE" ]; then
    echo "ERROR: URDF file not found at $URDF_FILE"
    exit 1
fi

echo "✓ URDF file found"
echo ""

echo "=== Processing Xacro to URDF ==="
xacro "$URDF_FILE" > /tmp/rosmower_test.urdf 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Xacro processing successful"
else
    echo "✗ Xacro processing failed"
    exit 1
fi

echo ""
echo "=== Validating URDF with check_urdf ==="
check_urdf /tmp/rosmower_test.urdf

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ URDF validation passed"
else
    echo ""
    echo "✗ URDF validation failed"
    exit 1
fi

echo ""
echo "=== Link Summary ==="
grep -oP '(?<=<link name=")[^"]+' /tmp/rosmower_test.urdf | sort | nl

echo ""
echo "=== Joint Summary ==="
grep -oP '(?<=<joint name=")[^"]+' /tmp/rosmower_test.urdf | sort | nl

echo ""
echo "=== Frame Tree ==="
urdf_to_graphiz /tmp/rosmower_test.urdf 2>/dev/null && echo "✓ Generated TF tree (see /tmp/rosmower_test.pdf if available)"

echo ""
echo "=== All checks complete! ==="

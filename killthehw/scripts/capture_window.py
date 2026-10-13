#!/usr/bin/env python3
"""Capture macOS application windows directly from background without stealing focus or Stage Manager distortion."""
import argparse
import ctypes
from ctypes import Structure, byref, c_bool, c_char_p, c_double, c_int, c_size_t, c_uint32, c_void_p
import os
from pathlib import Path
import subprocess
import sys


class CGPoint(Structure):
    _fields_ = [("x", c_double), ("y", c_double)]


class CGSize(Structure):
    _fields_ = [("width", c_double), ("height", c_double)]


class CGRect(Structure):
    _fields_ = [("origin", CGPoint), ("size", CGSize)]


def _load_frameworks():
    try:
        cg = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')
        cf = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
        imageio = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/ImageIO.framework/ImageIO')
    except Exception as e:
        sys.stderr.write(f"Error loading macOS frameworks: {e}\n")
        return None, None, None

    cg.CGMainDisplayID.restype = c_uint32
    cg.CGMainDisplayID.argtypes = []
    cg.CGMainDisplayID()

    cg.CGWindowListCopyWindowInfo.restype = c_void_p
    cg.CGWindowListCopyWindowInfo.argtypes = [c_uint32, c_uint32]

    cg.CGWindowListCreateImage.restype = c_void_p
    cg.CGWindowListCreateImage.argtypes = [CGRect, c_uint32, c_uint32, c_uint32]

    cg.CGImageGetWidth.restype = c_size_t
    cg.CGImageGetWidth.argtypes = [c_void_p]
    cg.CGImageGetHeight.restype = c_size_t
    cg.CGImageGetHeight.argtypes = [c_void_p]
    cg.CGImageRelease.restype = None
    cg.CGImageRelease.argtypes = [c_void_p]

    cf.CFArrayGetCount.restype = c_int
    cf.CFArrayGetCount.argtypes = [c_void_p]

    cf.CFArrayGetValueAtIndex.restype = c_void_p
    cf.CFArrayGetValueAtIndex.argtypes = [c_void_p, c_int]

    cf.CFDictionaryGetValue.restype = c_void_p
    cf.CFDictionaryGetValue.argtypes = [c_void_p, c_void_p]

    cf.CFStringCreateWithCString.restype = c_void_p
    cf.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, c_uint32]

    cf.CFStringGetCString.restype = c_int
    cf.CFStringGetCString.argtypes = [c_void_p, c_char_p, c_int, c_uint32]

    cf.CFNumberGetValue.restype = c_int
    cf.CFNumberGetValue.argtypes = [c_void_p, c_int, c_void_p]

    cf.CFURLCreateFromFileSystemRepresentation.restype = c_void_p
    cf.CFURLCreateFromFileSystemRepresentation.argtypes = [c_void_p, c_char_p, c_size_t, c_bool]

    cf.CFRelease.restype = None
    cf.CFRelease.argtypes = [c_void_p]

    imageio.CGImageDestinationCreateWithURL.restype = c_void_p
    imageio.CGImageDestinationCreateWithURL.argtypes = [c_void_p, c_void_p, c_size_t, c_void_p]
    imageio.CGImageDestinationAddImage.restype = None
    imageio.CGImageDestinationAddImage.argtypes = [c_void_p, c_void_p, c_void_p]
    imageio.CGImageDestinationFinalize.restype = c_bool
    imageio.CGImageDestinationFinalize.argtypes = [c_void_p]

    return cg, cf, imageio


def get_cf_string(cf, val):
    if not val:
        return ""
    buf = ctypes.create_string_buffer(1024)
    cf.CFStringGetCString(val, buf, 1024, 0x08000100)  # kCFStringEncodingUTF8
    return buf.value.decode('utf-8', errors='ignore')


def get_cf_number(cf, val):
    if not val:
        return 0
    num = ctypes.c_int32(0)
    cf.CFNumberGetValue(val, 3, byref(num))  # kCFNumberSInt32Type = 3
    return num.value


def list_windows(app_name=None, title_pattern=None, on_screen_only=False):
    cg, cf, _ = _load_frameworks()
    if not cg or not cf:
        return []

    k_owner = cf.CFStringCreateWithCString(None, b'kCGWindowOwnerName', 0x08000100)
    k_name = cf.CFStringCreateWithCString(None, b'kCGWindowName', 0x08000100)
    k_num = cf.CFStringCreateWithCString(None, b'kCGWindowNumber', 0x08000100)
    k_layer = cf.CFStringCreateWithCString(None, b'kCGWindowLayer', 0x08000100)
    k_pid = cf.CFStringCreateWithCString(None, b'kCGWindowOwnerPID', 0x08000100)

    option = 1 if on_screen_only else 0
    win_list = cg.CGWindowListCopyWindowInfo(option, 0)
    if not win_list:
        return []

    count = cf.CFArrayGetCount(win_list)
    results = []

    for i in range(count):
        dict_ref = cf.CFArrayGetValueAtIndex(win_list, i)
        owner = get_cf_string(cf, cf.CFDictionaryGetValue(dict_ref, k_owner))
        name = get_cf_string(cf, cf.CFDictionaryGetValue(dict_ref, k_name))
        wid = get_cf_number(cf, cf.CFDictionaryGetValue(dict_ref, k_num))
        layer = get_cf_number(cf, cf.CFDictionaryGetValue(dict_ref, k_layer))
        pid = get_cf_number(cf, cf.CFDictionaryGetValue(dict_ref, k_pid))

        if layer != 0:
            continue

        if app_name and app_name.lower() not in owner.lower():
            continue
        if title_pattern and title_pattern.lower() not in name.lower():
            continue

        results.append({
            "window_id": wid,
            "owner": owner,
            "title": name,
            "layer": layer,
            "pid": pid
        })

    return results


def capture_window_id(window_id, output_path, shadow=False):
    """Capture a specific window by ID directly from WindowServer backing store (immune to Stage Manager tilt)."""
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cg, cf, imageio = _load_frameworks()
    if cg and cf and imageio:
        rect_null = CGRect.in_dll(cg, "CGRectNull")
        # kCGWindowListOptionIncludingWindow = 8
        # kCGWindowImageBoundsIgnoreFraming = 1, kCGWindowImageBestResolution = 8
        img_opts = 8 if shadow else (1 | 8)
        img = cg.CGWindowListCreateImage(rect_null, 8, int(window_id), img_opts)
        if img:
            w = cg.CGImageGetWidth(img)
            h = cg.CGImageGetHeight(img)
            if w > 0 and h > 0:
                path_bytes = str(output_path).encode('utf-8')
                url = cf.CFURLCreateFromFileSystemRepresentation(None, path_bytes, len(path_bytes), False)
                uti_png = cf.CFStringCreateWithCString(None, b'public.png', 0x08000100)
                dest = imageio.CGImageDestinationCreateWithURL(url, uti_png, 1, None)
                ok = False
                if dest:
                    imageio.CGImageDestinationAddImage(dest, img, None)
                    ok = bool(imageio.CGImageDestinationFinalize(dest))
                    cf.CFRelease(dest)
                cf.CFRelease(uti_png)
                cf.CFRelease(url)
                cg.CGImageRelease(img)
                if ok and output_path.exists() and output_path.stat().st_size > 0:
                    return output_path
            else:
                cg.CGImageRelease(img)

    # Fallback to screencapture CLI
    cmd = ["screencapture", "-x", "-l", str(window_id)]
    if not shadow:
        cmd.append("-o")
    cmd.append(str(output_path))

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"screencapture failed: {res.stderr}")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"screencapture produced empty file for window {window_id}")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Capture macOS application window silently from background.")
    parser.add_argument("--app", help="Application name or partial owner name (e.g. 'Code', 'Wireshark', 'Finder')")
    parser.add_argument("--title", help="Window title match (optional)")
    parser.add_argument("--id", type=int, help="Exact Window ID to capture directly")
    parser.add_argument("--list", action="store_true", help="List matching windows and exit")
    parser.add_argument("--shadow", action="store_true", help="Keep window shadow (default: False)")
    parser.add_argument("--out", "-o", help="Output PNG path", default="window_capture.png")

    args = parser.parse_args()

    if args.list:
        windows = list_windows(app_name=args.app, title_pattern=args.title)
        print(f"Found {len(windows)} matching windows:")
        for w in windows:
            print(f"  [ID: {w['window_id']:<7}] App: {w['owner']:<20} Title: {w['title']}")
        return

    target_id = args.id
    if not target_id:
        if not args.app:
            parser.error("Please specify either --app, --id, or --list")
        windows = list_windows(app_name=args.app, title_pattern=args.title)
        if not windows:
            print(f"No active windows found for app '{args.app}'", file=sys.stderr)
            sys.exit(1)
        # Prefer windows with non-empty titles (main document windows over empty menu/overlay windows)
        titled = [w for w in windows if w["title"].strip()]
        chosen = titled[0] if titled else windows[0]
        target_id = chosen["window_id"]
        print(f"Found matching window: ID {target_id} ({chosen['owner']} - '{chosen['title']}')")

    out_file = capture_window_id(target_id, args.out, shadow=args.shadow)
    print(f"Successfully captured window {target_id} -> {out_file}")


if __name__ == "__main__":
    main()

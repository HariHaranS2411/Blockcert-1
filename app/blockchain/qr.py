import os
from pathlib import Path
import qrcode
from PIL import Image


def generate_certificate_qr(certificate_id: str, verify_url: str, output_dir: str) -> str:
    """
    Generate a high-resolution QR code image pointing to the public verification URL.
    Saves the image to output_dir and returns the relative or absolute filepath.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    filename = f"{certificate_id}_qr.png"
    filepath = output_path / filename

    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)

    # Generate image with deep navy primary theme
    img = qr.make_image(fill_color="#00236f", back_color="#ffffff")
    img.save(str(filepath))

    return str(filepath)

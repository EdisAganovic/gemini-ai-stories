#!/usr/bin/env python3
"""
Generator priča za djecu

Ovaj alat koristi Google Gemini API da generiše maštovite priče na osnovu dječijih crteža.
Sve priče se generišu na bosanskom jeziku.
"""

import os
import argparse
import sys
from pathlib import Path
from typing import Optional

import google.generativeai as genai
from PIL import Image

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()


def validate_image_path(image_path: str) -> bool:
    """Validate if the provided path is a valid image file."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file does not exist: {image_path}")

    valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    if path.suffix.lower() not in valid_extensions:
        raise ValueError(f"Unsupported image format: {path.suffix}. Supported formats are: {', '.join(valid_extensions)}")

    # Check if file is too large (optional but recommended for API calls)
    file_size = path.stat().st_size
    max_size = 20 * 1024 * 1024  # 20MB limit
    if file_size > max_size:
        raise ValueError(f"File size is too large: {file_size} bytes. Maximum allowed size is {max_size} bytes.")

    return True


def get_story_prompt(child_name: str, style: str, length: str, image_description: str) -> str:
    """Construct the prompt for story generation."""
    # Map English style names to Bosnian equivalents for use in the prompt
    style_mapping = {
        "fairy tale": "basna",
        "sci-fi": "naučna fantastika",
        "adventure": "pustolovina",
        "mystery": "misterija",
        "comedy": "komedija",
        "everyday life": "svakodnevni život"
    }
    
    bosnian_style = style_mapping.get(style, style)
    
    # Length description is already in Bosnian
    length_description = "5 paragrafa" if length == "short" else "10 paragrafa"

    prompt = f"""Napiši maštovitu i zanimljivu priču na bosanskom jeziku za dijete po imenu {child_name} na osnovu ovog crteža: {image_description}.

Priča treba biti u {bosnian_style} stilu i otprilike {length_description} duga.
Uvjeri se da je priča primjerena uzrastu djece, zabavna i da uključuje elemente koje se mogu vidjeti na crtežu.
Priča treba imati {child_name} kao glavni lik ili nekako povezati crtež sa avanturom {child_name}.

Započni priču sa: "Jednom davno, {child_name} je otkrio/la..."
Za basne stil možeš započeti sa "Priča se događa u jednom dalekom carstvu gdje živi..."
Završ priču sa: "...i tako se završila izuzetna avantura djeteta {child_name}!"

Učini priču kreativnom, pozitivnom i primjerenom za djecu. Sav tekst mora biti na bosanskom jeziku."""

    return prompt


def generate_story_with_gemini(image_path: str, child_name: str, style: str, length: str) -> str:
    """Generate a story using the Google Gemini API."""
    try:
        # Configure Gemini API
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

        # Create the prompt
        prompt = get_story_prompt(child_name, style, length, "ovaj crtež")
        
        # Load the image
        img = Image.open(image_path)
        
        # Select the model
        model = genai.GenerativeModel('gemini-flash-latest')
        
        # Generate content
        response = model.generate_content([prompt, img])
        
        return response.text

    except Exception as e:
        raise e


def get_user_input(image_path: Optional[str], child_name: Optional[str], style: Optional[str], length: Optional[str]) -> tuple:
    """Get user input for story generation parameters."""
    # Get image path if not provided via CLI
    if not image_path:
        image_path = input("Unesite putanju do dječijeg crteža (JPG, PNG, BMP ili WebP): ").strip()

    # Validate image path
    if not validate_image_path(image_path):
        raise ValueError(f"Neispravna datoteka sa slikom: {image_path}")

    # Get child's name if not provided via CLI
    if not child_name:
        child_name = input("Unesite ime djeteta: ").strip()
        if not child_name:
            raise ValueError("Ime djeteta ne može biti prazno")

    # Get story style if not provided via CLI
    valid_styles = ["fairy tale", "sci-fi", "adventure", "mystery", "comedy", "everyday life"]
    if not style:
        print("\nIzaberite stil priče:")
        print("  1. Basna (fairy tale)")
        print("  2. Naučna fantastika (sci-fi)")
        print("  3. Pustolovina (adventure)")
        print("  4. Misterija (mystery)")
        print("  5. Komedija (comedy)")
        print("  6. Svakodnevni život (everyday life)")

        while True:
            try:
                choice = input("Unesite vaš izbor (1-6): ").strip()
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(valid_styles):
                    style = valid_styles[choice_idx]
                    break
                else:
                    print("Molimo unesite broj između 1 i 6.")
            except (ValueError, IndexError):
                print("Molimo unesite ispravan broj.")

    # Get story length if not provided via CLI
    if not length:
        print("\nIzaberite dužinu priče:")
        print("  1. Kratka (oko 5 paragrafa) - short")
        print("  2. Duga (oko 10 paragrafa) - long")

        while True:
            try:
                choice = input("Unesite vaš izbor (1 ili 2): ").strip()
                if choice == "1":
                    length = "short"
                    break
                elif choice == "2":
                    length = "long"
                    break
                else:
                    print("Molimo unesite 1 ili 2.")
            except ValueError:
                print("Molimo unesite ispravan broj.")

    return image_path, child_name, style, length


def main():
    """Main function to run the CLI Story Generator."""
    parser = argparse.ArgumentParser(
        description="Generate imaginative stories based on children's drawings using Google Gemini API"
    )

    parser.add_argument(
        "-i", "--image",
        type=str,
        help="Path to the child's drawing (JPG, PNG, BMP, or WebP)"
    )

    parser.add_argument(
        "-n", "--name",
        type=str,
        help="Child's first name to personalize the story"
    )

    parser.add_argument(
        "-s", "--style",
        type=str,
        choices=["fairy tale", "sci-fi", "adventure", "mystery", "comedy", "everyday life"],
        help="Stil priče (fairy tale/basna, sci-fi/naučna fantastika, adventure/pustolovina, mystery/misterija, comedy/komedija, everyday life/svakodnevni život)"
    )

    parser.add_argument(
        "-l", "--length",
        type=str,
        choices=["short", "long"],
        help="Dužina priče (short/kratka: ~5 paragrafa, long/duga: ~10 paragrafa)"
    )

    args = parser.parse_args()

    # Check for API key
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable is not set.")
        print("Please set your Google Gemini API key before running this application.")
        sys.exit(1)

    try:
        # Get user input (either from CLI args or interactive prompts)
        image_path, child_name, style, length = get_user_input(
            args.image, args.name, args.style, args.length
        )

        print(f"\nGenerating a {length} {style} story for {child_name} based on {image_path}...\n")

        # Generate the story
        story = generate_story_with_gemini(image_path, child_name, style, length)

        if not story or story.strip() == "":
            print("Warning: The AI did not generate any story content. The image might not have recognizable elements or the API might have encountered an issue.")
            sys.exit(1)

        print("\n" + "="*60)
        print("YOUR CUSTOM STORY".center(60))
        print("="*60)
        print(story)
        print("="*60)

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
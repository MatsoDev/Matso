import customtkinter as ctk
import requests
import os
import threading
from datetime import datetime
import time
from urllib.parse import urlparse
import json

# Configuration
API_KEY = "Your API"
HEADERS = {"Authorization": API_KEY}
BASE_URL = "https://api.pexels.com/v1/search"

# Set appearance
ctk.set_appearance_mode("dark")

class ImageDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window configuration
        self.title("Pexels Image Downloader")
        self.geometry("600x800")
        self.minsize(500, 400)
        
        # State variables
        self.active_downloads = 0
        self.total_categories = 0
        self.completed_categories = 0
        self.is_downloading = False
        
        # Track downloaded images to prevent duplicates
        self.downloaded_images = set()  # Global set to track all downloaded image IDs
        self.load_existing_downloads()  # Load previously downloaded images
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(main_frame, text="Pexels Image Downloader", 
                                 font=ctk.CTkFont(size=24, weight="bold"))
        title_label.pack(pady=(20, 30))
        
        # Categories input
        self.label_categories = ctk.CTkLabel(main_frame, text="Enter Categories (comma separated):")
        self.label_categories.pack(pady=(0, 5))
        
        self.entry_categories = ctk.CTkEntry(main_frame, placeholder_text="e.g. technology, nature, cars",
                                           height=40)
        self.entry_categories.pack(pady=5, fill="x", padx=20)
        
        # Number of images input
        self.label_count = ctk.CTkLabel(main_frame, text="Number of images per category:")
        self.label_count.pack(pady=(15, 5))
        
        self.entry_count = ctk.CTkEntry(main_frame, placeholder_text="e.g. 30", height=40)
        self.entry_count.pack(pady=5, fill="x", padx=20)
        
        # Image quality selection
        self.label_quality = ctk.CTkLabel(main_frame, text="Image Quality:")
        self.label_quality.pack(pady=(15, 5))
        
        self.quality_var = ctk.StringVar(value="large")
        quality_frame = ctk.CTkFrame(main_frame)
        quality_frame.pack(pady=5, fill="x", padx=20)
        
        qualities = [("Original", "original"), ("Large", "large"), ("Medium", "medium")]
        for i, (text, value) in enumerate(qualities):
            radio = ctk.CTkRadioButton(quality_frame, text=text, variable=self.quality_var, value=value)
            radio.pack(side="left", padx=20, pady=10)
        
        # Download button
        self.download_btn = ctk.CTkButton(main_frame, text="Start Download", 
                                        command=self.start_download,
                                        height=40, font=ctk.CTkFont(size=16, weight="bold"))
        self.download_btn.pack(pady=20)
        
        # Progress section
        progress_frame = ctk.CTkFrame(main_frame)
        progress_frame.pack(fill="x", padx=20, pady=(10, 0))
        
        self.progress_label = ctk.CTkLabel(progress_frame, text="Progress:")
        self.progress_label.pack(pady=(10, 5))
        
        self.progress = ctk.CTkProgressBar(progress_frame, height=20)
        self.progress.pack(fill="x", padx=20, pady=(0, 10))
        self.progress.set(0)
        
        # Status display
        self.status_text = ctk.CTkTextbox(main_frame, height=100)
        self.status_text.pack(fill="x", padx=20, pady=(10, 20))
        
        # Stop button
        self.stop_btn = ctk.CTkButton(main_frame, text="Stop Download", 
                                    command=self.stop_download,
                                    state="disabled", fg_color="red", hover_color="darkred")
        self.stop_btn.pack(pady=(0, 20))
        
    def validate_input(self):
        """Validate user input"""
        categories_text = self.entry_categories.get().strip()
        count_text = self.entry_count.get().strip()
        
        if not categories_text:
            self.add_status("❌ Error: Please enter at least one category.")
            return None, None
            
        if not count_text.isdigit() or int(count_text) <= 0:
            self.add_status("❌ Error: Please enter a valid positive number for image count.")
            return None, None
            
        count = int(count_text)
        if count > 1000:
            self.add_status("❌ Error: Maximum 1000 images per category allowed.")
            return None, None
            
        categories = [cat.strip() for cat in categories_text.split(",") if cat.strip()]
        if len(categories) > 10:
            self.add_status("❌ Error: Maximum 10 categories allowed.")
            return None, None
            
        return categories, count
    
    def start_download(self):
        """Start the download process"""
        categories, count = self.validate_input()
        if not categories or not count:
            return
            
        # Reset state
        self.is_downloading = True
        self.active_downloads = 0
        self.total_categories = len(categories)
        self.completed_categories = 0
        
        # Update UI
        self.download_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress.set(0)
        self.status_text.delete("0.0", "end")
        
        self.add_status(f"🚀 Starting download for {len(categories)} categories...")
        self.add_status(f"📊 Total images to download: {len(categories) * count}")
        
        # Start downloads for each category
        for category in categories:
            if self.is_downloading:
                self.active_downloads += 1
                thread = threading.Thread(target=self.download_category_images, 
                                        args=(category, count), daemon=True)
                thread.start()
    
    def stop_download(self):
        """Stop all downloads"""
        self.is_downloading = False
        self.add_status("🛑 Stopping downloads...")
        self.stop_btn.configure(state="disabled")
        
        # Re-enable download button after a delay
        self.after(2000, self.reset_ui)
    
    def load_existing_downloads(self):
        """Load previously downloaded image IDs from all existing folders"""
        self.downloaded_images = set()
        
        try:
            # Get all folders in current directory that match our naming pattern
            for item in os.listdir('.'):
                if os.path.isdir(item) and '_20' in item:  # Our folders contain timestamp
                    for filename in os.listdir(item):
                        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                            # Extract image ID from filename (before the extension)
                            img_id = os.path.splitext(filename)[0]
                            self.downloaded_images.add(img_id)
            
            if self.downloaded_images:
                self.add_status(f"📥 Loaded {len(self.downloaded_images)} previously downloaded images")
            
        except Exception as e:
            self.add_status(f"⚠️ Warning: Could not load existing downloads: {str(e)}")
    
    def save_download_record(self, img_id, category, filepath):
        """Save record of downloaded image"""
        self.downloaded_images.add(img_id)
        
        # Optionally save to a log file for persistence
        try:
            with open('download_log.txt', 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"{timestamp},{img_id},{category},{filepath}\n")
        except Exception:
            pass  # Don't fail if we can't write to log
    
    def reset_ui(self):
        """Reset UI to initial state"""
        self.download_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress.set(0)
    
    def download_category_images(self, category, total_images):
        """Download images for a specific category"""
        if not self.is_downloading:
            return
            
        # Create folder with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        save_folder = f"{category.replace(' ', '_')}_{timestamp}"
        
        try:
            os.makedirs(save_folder, exist_ok=True)
            self.add_status(f"📁 Created folder: {save_folder}")
        except Exception as e:
            self.add_status(f"❌ Error creating folder for {category}: {str(e)}")
            self.download_finished()
            return
        
        page = 1
        downloaded = 0
        quality = self.quality_var.get()
        
        while downloaded < total_images and self.is_downloading:
            try:
                # API request
                params = {
                    'query': category,
                    'per_page': min(80, total_images - downloaded),  # Max 80 per request
                    'page': page
                }
                
                response = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=10)
                
                if response.status_code == 429:  # Rate limit
                    self.add_status(f"⏳ Rate limit reached for {category}, waiting...")
                    time.sleep(60)
                    continue
                    
                if response.status_code != 200:
                    self.add_status(f"❌ API Error for {category}: {response.status_code}")
                    break
                
                data = response.json()
                photos = data.get('photos', [])
                
                if not photos:
                    self.add_status(f"🔍 No more images found for '{category}'")
                    break
                
                # Download images
                for photo in photos:
                    if downloaded >= total_images or not self.is_downloading:
                        break
                        
                    img_id = str(photo['id'])
                    
                    # Check if this image was already downloaded globally
                    if img_id in self.downloaded_images:
                        self.add_status(f"⏭️ Skipped duplicate image {img_id} in '{category}'")
                        continue
                    
                    img_url = photo['src'].get(quality, photo['src']['large'])
                    
                    # Get file extension from URL
                    parsed_url = urlparse(img_url)
                    ext = os.path.splitext(parsed_url.path)[1] or '.jpg'
                    filepath = os.path.join(save_folder, f"{img_id}{ext}")
                    
                    # Double check if file exists in current folder
                    if os.path.exists(filepath):
                        self.downloaded_images.add(img_id)  # Add to tracking
                        continue
                    
                    try:
                        # Download image
                        img_response = requests.get(img_url, timeout=30)
                        img_response.raise_for_status()
                        
                        with open(filepath, 'wb') as f:
                            f.write(img_response.content)
                        
                        # Record the download
                        self.save_download_record(img_id, category, filepath)
                        
                        downloaded += 1
                        
                        # Update progress
                        progress = downloaded / total_images
                        self.update_progress(progress, category, downloaded, total_images)
                        
                        # Small delay to avoid overwhelming the API
                        time.sleep(0.1)
                        
                    except Exception as e:
                        self.add_status(f"⚠️ Failed to download image {img_id}: {str(e)}")
                        continue
                
                page += 1
                
            except Exception as e:
                self.add_status(f"❌ Error downloading {category}: {str(e)}")
                break
        
        # Completion message
        if self.is_downloading:
            self.add_status(f"✅ Completed '{category}': {downloaded}/{total_images} images")
        else:
            self.add_status(f"⏹️ Stopped '{category}': {downloaded}/{total_images} images")
        
        self.download_finished()
    
    def update_progress(self, progress, category, downloaded, total):
        """Update progress bar and status"""
        def update():
            overall_progress = (self.completed_categories + progress) / self.total_categories
            self.progress.set(overall_progress)
            
        self.after(0, update)
    
    def download_finished(self):
        """Handle completion of a category download"""
        self.active_downloads -= 1
        self.completed_categories += 1
        
        if self.active_downloads <= 0:
            # All downloads finished
            def finish():
                self.progress.set(1.0)
                if self.is_downloading:
                    self.add_status("🎉 All downloads completed successfully!")
                else:
                    self.add_status("⏹️ Downloads stopped by user")
                self.reset_ui()
                
            self.after(0, finish)
    
    def add_status(self, message):
        """Add status message to the text display"""
        def update():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.status_text.insert("end", f"[{timestamp}] {message}\n")
            self.status_text.see("end")
            
        self.after(0, update)


if __name__ == "__main__":
    try:
        app = ImageDownloaderApp()
        app.mainloop()
    except Exception as e:
        print(f"Error starting application: {e}")

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from multiprocessing import Process
from glob import glob
from pdf2image import convert_from_path
from fpdf import FPDF
from PIL import Image
from time import sleep
import argparse
import shutil
import json
import os
import logging


config = {
    'input': {
        'pdfs_path': 'pdfs',
        'images_path': 'images'
    },
    'output': {
        'pdfs_path': 'output/pdfs',
        'images_path': 'output/images'
    }
}


class PDF2ImagesFSEventHandler(FileSystemEventHandler):
    def on_closed(self, event):
        if event.src_path.endswith('.pdf'):
            print('Starting splitting pdf to images')
            split_pdf(event.src_path)
            os.remove(event.src_path)
            print('Finish splitting pdf to images')


class Images2PDFFSEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith('.txt'):
            print('Starting joining images to pdfs')
            pdf_name = open(event.src_path).read().strip()
            os.remove(event.src_path)
            join_images(pdf_name)
            print('Finish joining images to pdfs')


def images_dir_watcher(images_path):
    while True:
        print('Started images watcher')
        try:
            event_handler = Images2PDFFSEventHandler()
            observer = Observer()
            observer.schedule(event_handler, images_path)
            observer.start()
            while True:
                sleep(1)
            print('Stopped images watcher')
        except KeyboardInterrupt:
            observer.join()
            observer.stop()


def pdfs_dir_watcher(pdfs_path):
    while True:
        print('Started PDFs watcher')
        try:
            event_handler = PDF2ImagesFSEventHandler()
            observer = Observer()
            observer.schedule(event_handler, pdfs_path)
            observer.start()
            while True:
                sleep(1)
            print('Stopped PDFs watcher')
        except KeyboardInterrupt:
            observer.join()
            observer.stop()


def split_pdf(pdf_path):
    try:
        print(f"Splitting {pdf_path}")
        pdf_images_path = pdf_path.split('/')[-1].rsplit('.', 1)[0]
        os.makedirs(f"{config['output']['images_path']}/{pdf_images_path}", exist_ok=True)
        pages = convert_from_path(pdf_path)
        for i in range(len(pages)):
            print(f"Page {i+1}/{len(pages)}")
            page_num = str(i + 1).zfill(4)
            pages[i].save(f"{config['output']['images_path']}/{pdf_images_path}/page-{page_num}.jpg", 'JPEG')
        print(f"Splitting {pdf_path} done")
        # os.remove(pdf_path)
    except Exception as e:
        print(str(e))


def join_images(pdf_name):
    try:
        print(f"Joining {pdf_name}")
        pdf_name_prefix = pdf_name.rsplit('.', 1)[0]
        images = []
        for extension in ['jpg', 'jpeg', 'png', 'tiff', 'bmp', 'jfif']:
            for image in glob(f'{config["input"]["images_path"]}/**/*.{extension}', recursive=True):
                images.append(image)
        images.sort()
        #
        pdf = FPDF()
        print(f"Joining to full {pdf_name}")
        for image in images:
            print(f"Joining {image}")
            img = Image.open(image)
            width, height = img.size
            width, height = float(width * 0.264583), float(height * 0.264583)
            pdf.add_page(format=(width, height))
            pdf.image(img, 0, 0, width, height)
        pdf.output(f"{config['output']['pdfs_path']}/{pdf_name_prefix}_max.pdf")
        #
        print(f"Resizing images to save space")
        output_pdf_path = f"{config['output']['pdfs_path']}/{pdf_name_prefix}_min.pdf"
        quality, size_ratio = 75, 0.9
        while sum(os.path.getsize(image) for image in images) / 1024 > 1024 and quality > 1:
            print(f"{sum(os.path.getsize(image) for image in images) / 1024:.2f} KB")
            for image in images:
                print(f"Resizing {image}")
                with Image.open(image) as img:
                    new_width, new_height = int(img.width * size_ratio), int(img.height * (img.width * size_ratio / img.width))
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                    img.save(image, quality=quality, optimize=True)
            quality = int(quality * 0.75)
        print(f"Resizing images to save space done")
        #
        pdf = FPDF()
        print(f"Joining to minimized {pdf_name}")
        for image in images:
            print(f"Joining {image}")
            img = Image.open(image)
            width, height = img.size
            width, height = float(width * 0.264583), float(height * 0.264583)
            pdf.add_page(format=(width, height))
            pdf.image(img, 0, 0, width, height)
        pdf.output(output_pdf_path)
        #
        output_pdf_filesize = os.path.getsize(output_pdf_path)
        print(f"{output_pdf_filesize / 1024:.2f} KB")
        while output_pdf_filesize > 1024 * 1024:
            print(f"Resizing images to save space")
            print(f"{sum(os.path.getsize(image) for image in images) / 1024:.2f} KB")
            for image in images:
                print(f"Resizing {image}")
                with Image.open(image) as img:
                    new_width, new_height = int(img.width * size_ratio), int(
                        img.height * (img.width * size_ratio / img.width))
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                    img.save(image, quality=quality, optimize=True)
            quality = int(quality * 0.75)
            print(f"Resizing images to save space done")
            #
            pdf = FPDF()
            print(f"Joining to {pdf_name}")
            for image in images:
                print(f"Joining {image}")
                img = Image.open(image)
                width, height = img.size
                width, height = float(width * 0.264583), float(height * 0.264583)
                pdf.add_page(format=(width, height))
                pdf.image(img, 0, 0, width, height)
            pdf.output(output_pdf_path)
            output_pdf_filesize = os.path.getsize(output_pdf_path)
        print(f"Joining {pdf_name} done")
        #
        print(f"Cleaning up")
        for image in images:
            os.remove(image)
        print(f"Cleaning up done")
        print(f"Joining {pdf_name} to pdfs done")
        for _dir in os.listdir(config['input']['images_path']):
            shutil.rmtree(f"{config['input']['images_path']}/{_dir}")
    except Exception as e:
        print(str(e))


def main():
    for type_key in config:
        os.makedirs(config[type_key]['pdfs_path'], exist_ok=True)
        os.makedirs(config[type_key]['images_path'], exist_ok=True)
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    pdfs_watcher, images_watcher = [
        Process(target=pdfs_dir_watcher, args=(config['input']['pdfs_path'],)),
        Process(target=images_dir_watcher, args=(config['input']['images_path'],))
    ]
    pdfs_watcher.start()
    images_watcher.start()
    #
    while True:
        for _process in [pdfs_watcher, images_watcher]:
            _process.join()
            if not _process.is_alive():
                exit(1)
        sleep(1)


if __name__ == '__main__':
    main()


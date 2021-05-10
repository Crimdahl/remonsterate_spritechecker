import os, datetime
from PIL import Image

log_file = None
total_sprites = 0
total_sprites_tmc = 0
total_sprites_wasteful = 0
total_sprites_transparent_top_row = 0

def main():
    global log_file
    global total_sprites
    global total_sprites_tmc
    global total_sprites_wasteful
    global total_sprites_transparent_top_row
    try:
        log_file = open("SpriteCheckerLog.txt", "a+")
    except IOError as e:
        print("Error using log file: " + str(e))
    try:
        #Populate the file name lists. Iterates through directories starting at the
        #   directory containing the exe file. Does not traverse directories past
        #   the depth specified by walk_distance.
        walk_distance = 4
        exe_directory = os.path.abspath(".")
        exe_directory_level = exe_directory.count(os.path.sep)
        log("Looking for and analyzing png files in " + exe_directory + " and " + str(walk_distance) + " levels of subfolders.")
        for root, dirs, files in os.walk("."):
            current_walking_directory = os.path.abspath(root)
            current_directory_level = current_walking_directory.count(os.path.sep)
            if current_directory_level > exe_directory_level + walk_distance:
                #del dirs[:] empties the list that os.walk uses to determine what
                #   directories to walk through, meaning os.walk will move on to
                #   the next directory. It does NOT delete or modify files on the
                #   hard drive.
                if len(dirs) > 0:
                    log("There were additional unexplored directories in " + current_walking_directory + ".")
                del dirs[:] 
            else:
                for file_name in files:
                    if file_name.endswith(".png"):
                        total_sprites = total_sprites + 1
                        check_image(Image.open(os.path.join(current_walking_directory, file_name)))
        log("Total sprites: " + str(total_sprites))
        log("Sprites with correct colors: " + str(total_sprites - total_sprites_tmc - total_sprites_wasteful))
        log("Sprites with too many colors: " + str(total_sprites_tmc))
        log("Sprites with wasteful palettes: " + str(total_sprites_wasteful))
        log("Sprites with transparent top rows: " + str(total_sprites_transparent_top_row))
    except Exception as e:
        log("Exception encountered: " + str(e))
    finally:
        log_file.close()

def check_image(image: Image):
    global total_sprites_tmc
    global total_sprites_wasteful
    global total_sprites_transparent_top_row

    palette_indexes = set(image.tobytes())

    #Check if the image has too many colors
    if max(palette_indexes) > 0xf:
        log('INFO: %s has too many colors.' % image.filename)
        total_sprites_tmc = total_sprites_tmc + 1

    #Check if the image is wasting colors (why?)
    is_8color = max(palette_indexes) <= 7
    if (len(palette_indexes) <= 8 and not is_8color and hasattr(image, 'filename')):
        log('INFO: %s has a wasteful palette.' % image.filename)
        total_sprites_wasteful = total_sprites_wasteful + 1

    #Check if the top row of the image is transparent
    image_width_in_pixels, image_height_in_pixels = image.size
    pixel_data = image.convert('RGBA')
    transparent_top_row = True
    for x in range(image_width_in_pixels):
        r, g, b, a = pixel_data.getpixel((x, 0))
        if a > 0:
            transparent_top_row = False
        if x == image_width_in_pixels - 1 and transparent_top_row:
            log('WARNING: %s has a transparent top row.' % image.filename)
            total_sprites_transparent_top_row = total_sprites_transparent_top_row + 1

def log(line):
    #Log to both console and file
    global log_file
    print(line)
    if log_file: log_file.writelines(str(datetime.datetime.now()) + " " + line + "\n")

if __name__ == '__main__':
    try:
        main()
        input("Press any key to exit.")
    except Exception as e:
        print(str(e))
        input("Press any key to exit.")
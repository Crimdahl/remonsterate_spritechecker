import os
import datetime
from PIL import Image, ImageOps
from collections import Counter

exe_directory = os.getcwd()
try:
    log_file = open("SpriteCheckerLog.txt", "a+")
except IOError as e:
    print("Error using log file: " + str(e))
total_sprites = 0
total_sprites_unchanged = 0
total_sprites_tmc = 0
total_sprites_expanded = 0
total_sprites_cropped = 0


def main():
    global exe_directory
    global log_file
    global total_sprites
    global total_sprites_unchanged
    global total_sprites_tmc
    global total_sprites_expanded
    global total_sprites_cropped

    try:
        # Populate the file name lists. Iterates through directories starting at the
        #   directory containing the exe file. Does not traverse directories past
        #   the depth specified by walk_distance.
        walk_distance = 6
        exe_directory_level = exe_directory.count(os.path.sep)
        log("Looking for and analyzing png files in " + exe_directory + " and " + str(walk_distance) +
            " levels of sub-directories.")
        for root, dirs, files in os.walk(exe_directory):
            current_walking_directory = os.path.abspath(root)
            if "backup" in current_walking_directory:
                continue
            current_directory_level = current_walking_directory.count(os.path.sep)
            if current_directory_level > exe_directory_level + walk_distance:
                # del dirs[:] empties the list that os.walk uses to determine what
                #   directories to walk through, meaning os.walk will move on to
                #   the next directory. It does NOT delete or modify files on the
                #   hard drive.
                if len(dirs) > 0:
                    log("There were additional unexplored directories in " + current_walking_directory + ".")
                del dirs[:]
            else:
                for file_name in files:
                    if file_name.lower().endswith(".png"):
                        total_sprites = total_sprites + 1
                        check_image(Image.open(os.path.join(current_walking_directory, file_name)),
                                    current_walking_directory)
        log("Total sprites: " + str(total_sprites))
        log("Total sprites unchanged: " + str(total_sprites_unchanged))
        log("Sprites that had too many colors and were converted: " + str(total_sprites_tmc))
        log("Sprites that had excess top and/or left borders and were cropped: " + str(total_sprites_cropped))
        log("Sprites that had the bottom and/or right border expanded: " + str(total_sprites_expanded))
    except Exception as e2:
        log("Exception encountered: " + str(e2))
    finally:
        log_file.close()


def get_transparency(image: Image):
    width, height = image.size
    border = (
            [image.getpixel((0, j)) for j in range(height)] +
            [image.getpixel((width - 1, j)) for j in range(height)] +
            [image.getpixel((i, 0)) for i in range(width)] +
            [image.getpixel((i, height - 1)) for i in range(width)])
    transparency = Counter(border).most_common(1)[0][0]
    return transparency


def check_image(image: Image, current_directory: str):
    global exe_directory
    global total_sprites_unchanged
    global total_sprites_tmc
    global total_sprites_expanded
    global total_sprites_cropped

    allowed_colors = 0xf
    image_changed = False
    image_filename = image.filename
    palette_indexes = set(image.tobytes())

    # Check if the image has too many colors. If so, convert to 16-bit indexed.
    if max(palette_indexes) > allowed_colors:
        if image.mode == "P":
            # Images already in P mode cannot be converted to P mode to shrink their allowed colors, so
            #   temporarily convert them back to RGB
            image = image.convert("RGBA")
        image = image.convert("P", palette=Image.ADAPTIVE, colors=allowed_colors)
        image_changed = True
        total_sprites_tmc = total_sprites_tmc + 1
        log('Reduced the number of colors to the maximum supported (' + str(allowed_colors) + '): ' + image_filename)

    # Check if the top row and left column of the image are excess border
    image = image.convert('RGBA')
    border_color = get_transparency(image)
    solid_top = True
    solid_left = True
    had_transparent_border = False

    image_width_in_pixels, image_height_in_pixels = image.size
    while solid_top:
        current_color = border_color
        for x in range(image_width_in_pixels):
            # Scan the top row of pixels, cropping out the row if it is fully transparent
            if not current_color == image.getpixel((x, 0)):
                solid_top = False
            if not solid_top:
                break
            if x == image_width_in_pixels - 1 and solid_top:
                # If the top row was fully transparent, crop it out
                had_transparent_border = True
                image = image.crop((0, 1, image_width_in_pixels, image_height_in_pixels))
                image_width_in_pixels, image_height_in_pixels = image.size

    while solid_left:
        current_color = border_color
        for y in range(image_height_in_pixels):
            # Scan the left column of pixels, cropping out the column if it is fully transparent
            if not current_color == image.getpixel((0, y)):
                solid_left = False
            if not solid_left:
                break
            if y == image_height_in_pixels - 1 and solid_left:
                # If the left column was fully transparent, crop it out
                had_transparent_border = True
                image = image.crop((1, 0, image_width_in_pixels, image_height_in_pixels))
                image_width_in_pixels, image_height_in_pixels = image.size

    if had_transparent_border:
        log('Cropped extra border space from the top row and left column: ' + image_filename + '.')
        image_changed = True
        total_sprites_cropped = total_sprites_cropped + 1

    # Tiles are 8x8, so we ensure the image's width and height are divisible by 8
    image_width_in_pixels, image_height_in_pixels = image.size
    image_expanded = False
    if not image_width_in_pixels % 8 == 0:
        image_changed = True
        image_expanded = True
        border_width = 8 - (image_width_in_pixels % 8)
        image = ImageOps.expand(image, border=(0, 0, border_width, 0), fill=border_color)

    if not image_height_in_pixels % 8 == 0:
        image_changed = True
        image_expanded = True
        border_width = 8 - (image_height_in_pixels % 8)
        image = ImageOps.expand(image, border=(0, 0, 0, border_width), fill=border_color)

    if image_expanded:
        total_sprites_expanded = total_sprites_expanded + 1
        log('Expanded the right and bottom borders to fill an 8x8 tile: ' + image_filename)

    if image_changed:
        # Move the old file to a backup location
        image.filename = image_filename
        image = image.convert("P", palette=Image.ADAPTIVE, colors=allowed_colors)
        backup_location = os.path.join(exe_directory,
                                       "backup",
                                       current_directory[len(exe_directory) + 1:],
                                       image_filename[len(current_directory) + 1:])
        os.makedirs(os.path.dirname(backup_location), exist_ok=True)
        os.replace(src=image_filename, dst=backup_location)
        image.save(image_filename)
    else:
        total_sprites_unchanged = total_sprites_unchanged + 1


def log(line):
    # Log to both console and file
    global log_file
    print(line)
    if log_file:
        log_file.writelines(str(datetime.datetime.now()) + " " + line + "\n")


if __name__ == '__main__':
    try:
        print('This program will look through ALL .png files in the programs directory and up to 4 '
              'sub-directories.')
        print('If a sprite has more than 15 colors, it will be converted to use only 15 colors.')
        print('If a sprite has a excess border space on the top or left, it will be cropped.')
        print('If a sprite does not evenly fill an 8x8 tile, the bottom and/or right borders will be expanded.')
        print('The original image is saved in a backup directory in the script directory.')
        run_script = input('Continue? Y/N:  ')
        if run_script.lower() == "y":
            main()
        input("Press any key to exit.")
    except Exception as e:
        print(str(e))
        input("Press any key to exit.")

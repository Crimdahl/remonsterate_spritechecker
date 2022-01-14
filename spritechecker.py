import os
import datetime
from PIL import Image

exe_directory = os.getcwd()
try:
    log_file = open("SpriteCheckerLog.txt", "a+")
except IOError as e:
    print("Error using log file: " + str(e))
total_sprites = 0
total_sprites_tmc = 0
total_sprites_wasteful = 0
total_sprites_transparent_top_row = 0


def main():
    global exe_directory
    global log_file
    global total_sprites
    global total_sprites_tmc
    global total_sprites_wasteful
    global total_sprites_transparent_top_row

    try:
        # Populate the file name lists. Iterates through directories starting at the
        #   directory containing the exe file. Does not traverse directories past
        #   the depth specified by walk_distance.
        walk_distance = 4
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
                    if file_name.endswith(".png"):
                        total_sprites = total_sprites + 1
                        check_image(Image.open(os.path.join(current_walking_directory, file_name)),
                                    current_walking_directory)
        log("Total sprites: " + str(total_sprites))
        log("Sprites with correct colors: " + str(total_sprites - total_sprites_tmc - total_sprites_wasteful))
        log("Sprites with too many colors: " + str(total_sprites_tmc))
        log("Sprites with wasteful palettes: " + str(total_sprites_wasteful))
        log("Sprites with transparent border row or column: " + str(total_sprites_transparent_top_row))
    except Exception as e2:
        log("Exception encountered: " + str(e2))
    finally:
        log_file.close()


def check_image(image: Image, current_directory: str):
    global exe_directory
    global total_sprites_tmc
    global total_sprites_wasteful
    global total_sprites_transparent_top_row

    allowed_colors = 15
    image_changed = False
    image_filename = image.filename
    palette_indexes = set(image.tobytes())

    # Check if the image has too many colors. If so, convert to 16-bit indexed.
    if max(palette_indexes) > allowed_colors:
        log('Converted: ' + image_filename + ' had ' + str(max(palette_indexes)) +
            ' colors, which is more than the maximum allowed (' + str(allowed_colors) + ').')
        if image.mode == "P":
            # Images already in P mode cannot be converted to P mode to shrink their allowed colors, so
            #   temporarily convert them back to RGB
            image = image.convert("RGB")
        image = image.convert("P", palette=Image.ADAPTIVE, colors=allowed_colors)
        image_changed = True
        total_sprites_tmc = total_sprites_tmc + 1

    # Check if the image is wasting colors (why?)
    # is_8color = max(palette_indexes) <= 7
    # if len(palette_indexes) <= 8 and not is_8color and hasattr(image, 'filename'):
    #    log('INFO: %s has a wasteful palette.' % image_filename)
    #    total_sprites_wasteful = total_sprites_wasteful + 1

    # Check if the top row of the image is transparent
    transparent_top = True
    transparent_bottom = True
    transparent_left = True
    transparent_right = True
    had_transparent_border = False
    image_width_in_pixels, image_height_in_pixels = image.size

    while transparent_top or transparent_bottom or transparent_left or transparent_right:
        pixel_data = image.convert('RGBA')
        for x in range(image_width_in_pixels):
            # Scan the top and bottom rows of pixels, cropping out the row if it is fully transparent
            current_alpha_1 = pixel_data.getpixel((x, 0))[3]
            current_alpha_2 = pixel_data.getpixel((x, image_height_in_pixels - 1))[3]
            if not current_alpha_1 == 0:
                transparent_top = False
            if not current_alpha_2 == 0:
                transparent_bottom = False
            if not transparent_top and not transparent_bottom:
                break
            if x == image_width_in_pixels - 1 and transparent_top:
                # If the top row was fully transparent, crop it out
                image = image.crop((0, 1, image_width_in_pixels, image_height_in_pixels))
                image_width_in_pixels, image_height_in_pixels = image.size
                had_transparent_border = True
            if x == image_width_in_pixels - 1 and transparent_bottom:
                # If the bottom row was fully transparent, crop it out
                image = image.crop((0, 0, image_width_in_pixels, image_height_in_pixels - 1))
                image_width_in_pixels, image_height_in_pixels = image.size
                had_transparent_border = True

        for y in range(image_height_in_pixels):
            # Scan the left and right columns of pixels, cropping out the column if it is fully transparent
            current_alpha_3 = pixel_data.getpixel((0, y))[3]
            current_alpha_4 = pixel_data.getpixel((image_width_in_pixels - 1, y))[3]
            if current_alpha_3 and not current_alpha_3 == 0:
                transparent_left = False
            if current_alpha_4 and not current_alpha_4 == 0:
                transparent_right = False
            if not transparent_left and not transparent_right:
                break
            if y == image_height_in_pixels - 1 and transparent_left:
                # If the left column was fully transparent, crop it out
                image = image.crop((1, 0, image_width_in_pixels, image_height_in_pixels))
                image_width_in_pixels, image_height_in_pixels = image.size
                had_transparent_border = True
            if y == image_height_in_pixels - 1 and transparent_right:
                # If the right column was fully transparent, crop it out
                image = image.crop((0, 0, image_width_in_pixels - 1, image_height_in_pixels))
                image_width_in_pixels, image_height_in_pixels = image.size
                had_transparent_border = True
    if had_transparent_border:
        log('Cropped: ' + image_filename + ' had a transparent border row or column.')
        image_changed = True
        total_sprites_transparent_top_row = total_sprites_transparent_top_row + 1

    if image_changed:
        # Move the old file to a backup location
        image.filename = image_filename
        backup_location = os.path.join(exe_directory,
                                       "backup",
                                       current_directory[len(exe_directory) + 1:],
                                       image_filename[len(current_directory) + 1:])
        os.makedirs(os.path.dirname(backup_location), exist_ok=True)
        os.replace(src=image_filename, dst=backup_location)
        image.save(image_filename)


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
        print('If a .png file has more than 15 colors, it will be converted to use only 15 colors.')
        print('If it has a transparent border row or column, it will be cropped.')
        print('The original image is saved in a backup directory.')
        run_script = input('Continue? Y/N:  ')
        if run_script.lower() == "y":
            main()
        input("Press any key to exit.")
    except Exception as e:
        print(str(e))
        input("Press any key to exit.")

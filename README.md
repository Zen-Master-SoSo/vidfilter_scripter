# vidfilter_scripter

An **mpv** front-end which creates a mencoder script with video adjustments. The script reencodes your video with the correct adjustments using **ffmpeg**.

## Installation

You must have libmpv-dev and ffmpeg installed on your computer. On a debian based system using apt, run the following:

```bash
$ sudo apt install libmpv-dev ffmpeg
```

Install vidfilter_scripter using pip:

```bash
pip install vidfilter_scripter
```

### Usage

Preview the video you wish to reencode, adjusting brightness, contrast, hue,
saturation, and gamma:

<img width="932" height="449" alt="Main window" src="https://github.com/user-attachments/assets/77896cbe-a682-463a-bf07-30d347e25509" />

When you are satisfied, click the "Create script" button. The created menocoder
script will be shown with a "Save as" function available to save it to disk.

<img width="787" height="584" alt="Script generation popup" src="https://github.com/user-attachments/assets/60e3c806-0111-4d30-b3bf-7f6249edd0f9" />

Save the script and run it. You can run a script in the background using "at":

```bash
$ realpath reencode.sh | at now
```
...or...

```bash
$ realpath reencode.sh | batch
```
Or if you have more than one computer, you run it on the one in the closet at night!

```bash
$ realpath reencode.sh | at midnight
```


### Custom script

You can always change the script before running it. 

I chose some decent encoding options for one of several common video heights. 
You can replace those lines with your own preferece, if you want.

The purpose of this "program" is not to be a complete reeencoder. It is to be 
able to preview the video filter settings as you modify them, and then generate 
a correct video filter option to pass to ffmpeg for reencoding.


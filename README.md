# Unrefined Sequencing Format
![USF Logo](https://user-images.githubusercontent.com/76560493/211200052-f2da2b69-30b6-4049-8653-dbe08c34e21a.png)

A crude sample-based sequencing format developed in Python.

## Requirements

- **PyAudio** - for playback and recording (this is the only library you should have to install, and PortAudio if necessary)
- **Time** - used to calculate the rendering times
- **JSON** - parses the .usf files
- **OS** - gets the file path
- **ArgParse** - allows for command line usage
- **Wave** - for saving headered wave files

## Introduction

The Unrefined Sequencing Format is my attempt at creating a tracker-style music format. It is best used for phrase sampling and one-shot samples, or anything that doesn't rely on chromatic pitching. The whole reason I made it is because I wanted to try out some audio maths. It supports sample offsets, pitching and volume, and uses patterns which can be chained together to form a song.

## Files

Note: to view these programs' arguments, use the option -h at the command line.

- **unrefined.py** - The main replayer. The only required argument is the file to play, so in most operating systems, you can simply drag a file onto it! By default, the sound is rendered to a file called "result.wav" (or "result.raw" if you use the --raw/-r option), but you can use the --file_name/-f option to specify a custom file name without the extension; .wav or .raw will be added automatically.
- **play.py** - Plays a sound.
- **offset.py** - Plays a section of a sample based off a hex (or decimal) offset. It defaults to hex to make finding offsets easier!
- **record.py** - Records a sound straight from your computer! You also have the option to truncate the start and end automatically, so you can set a long recording time, and the program will pick the most important part, saving memory.
- **reverse.py** - Reverses a sound.
- **mirror.py** - "Mirrors" a sound by playing it normally up to a certain point, then playing it backwards.
- **echo.py** - Adds a simple delay effect to a sound.
- **lowpass.py** - Adds a rudimentary low-pass filter to a sound. You can filter it numerous times in one go to achieve a more muffled sound. There's also the option to use 32-bit accuracy (as opposed to 8-bit), which takes slightly longer, but results in a much smoother, albeit noisy sound.
- **timestretch.py** - Time-stretches a sound by repeating a portion of it numerous times.
- **speed.py** - Changes the speed of a sample by skipping or repeating bytes. Use this to increase the pitch range of a sample, or even crisp it up by slowing it down, and using double the sample rate!
- **truncate.py** - Trims a sound.
- **join.py** - Appends one sound onto the end of another. It's advisable to use "truncate.py" on each sample first to ensure the cleanest of splices! This also doubles as a mixing program, where you can combine two samples to play at the same time.
- **loudness.py** - Makes a sound louder or quieter.
- **fatten.py** - "Fattens" a sample by boosting the lows and highs, keeping the mids as-is. Obesity is fixed, because no other value seemed to generate the desired effect!
- **16to8.py** - Converts a 16-bit signed wave file to an 8-bit unsigned raw file, for processing through the effects/using in your songs.
- **interpolate.py** - Linearly interpolates a sample, producing a file at half speed with reduced aliasing. There's an optional low-pass filter to achieve an even smoother sound. Here's the difference it can make:

![Interpolation difference](https://user-images.githubusercontent.com/76560493/211199897-ad923fac-ac61-4627-a46c-ca4a9c17581e.png)

- **gargle.py** - Cuts the sample's volume at a rapid speed, resulting in a similar sound to a ring modulator.
- **oscillate.py** - Generates a raw file containing a sine or square wave at variable frequency. 
- **additive.py** - Additive synthesis tool.
- **topper.py** - Stops the waveform from going above a certain amplitude.
- **format.py** - Converts an old .usf file to the new, readable format.
- **prefs.py** - A library that's used behind the scenes to load the preferences file. Nothing you need to worry about!
- **unrefined_gui.py** - An unfinished GUI for creating .usf files. This'll probably never get finished.

## Technical Information

The replayer creates the resulting file by calculating the length of the song in samples, then going through each track, working out which sample to play and which byte from the sample it should add, based off the speed, volume and offset parameters. Each track is rendered to an external file, before being read back and summed together to create a file containing your glorious composition! 8-bit and 16-bit samples are both supported, raw or headered, mono or stereo, signed or unsigned!

Mixing sounds together by adding numbers does have a limitation. If you were to add 2 sounds together, you could easily do that by adding the numbers - but only if they were 127 or below. If the sum happened to be above 255, it would cause an overflow since we're dealing with 8-bit sounds, and that's the highest unsigned 8-bit number. To get around this, we divide the sum by 2, as we're mixing 2 sounds. The result is half the volume, but you get both sounds. The same applies for 16-bit sounds, where 127 = 32767 and 255 = 65535.

## File Format

.usf files are actually .json files, just very indiscreetly renamed! I'm using them because .json files are awesome, and they handle arrays natively, which is an absolute godsend. I could create an entire format myself, but that's far beyond my intentions.

A .usf file consists of numerous sections:

**"samples"** - List of samples in sequential order. When using samples, remember that they start from 1, as 0 is assumed blank. If all of your samples are in a raw, 8-bit unsigned format, they can be stored as a simple array, like so:

```
"samples": [
	"sample1.raw",
	"sample2.raw",
	"sample3.raw"
]
```

If you want to use stereo or 16-bit samples, they're stored a bit differently:

```
"samples": [
	["sample1.raw",0,0,1],
	["sample2.raw",1,0,0],
	["sample3.raw",1,1,1]
]
```

The first parameter is of course, the sample name. The second parameter selects an 8-bit or 16-bit sample, the third parameter selects mono or stereo, and the fourth parameter selects unsigned or signed (all parameters take 0 or 1 as the value). When using stereo samples, only the left channel will be used. Note that sample names are relative to the .usf file, so it'll look for samples in the same directory. You can use samples from directories above the file, but not below. For instance, "folder/sample.raw" is possible, but "../sample.raw" is not.

**"patterns"** - List of pattern objects, each containing the name (used in the arrangement), and a 2D array containing the pattern data.

In the original format, each index of the array refers to the track, and each sub-index contains the list of lines. So, a 2-track pattern would look something like this:

```
[ -- start of pattern
	[ -- track 1
		"00 00 00 00",
		"00 00 00 00"
		etc..
	], -- end of track 1
	[ -- track 2
		"00 00 00 00",
		"00 00 00 00"
		etc..
	] -- end of track 2
] -- end of pattern
```

However, writing simple patterns proved very tedious, as each track was stored individually. So, a new format was introduced to alleviate this issue! Patterns are now laid out identically to trackers:

```
[ -- start of pattern
	-- track 1     -- track 2    -- track 3    -- track 4
	["00 00 00 00","00 00 00 00","00 00 00 00","00 00 00 00"], -- line 1
	["00 00 00 00","00 00 00 00","00 00 00 00","00 00 00 00"], -- line 2
	["00 00 00 00","00 00 00 00","00 00 00 00","00 00 00 00"], -- line 3
	["00 00 00 00","00 00 00 00","00 00 00 00","00 00 00 00"], -- line 4
	["00 00 00 00","00 00 00 00","00 00 00 00","00 00 00 00"], -- line 5
	["00 00 00 00","00 00 00 00","00 00 00 00","00 00 00 00"], -- line 6
	["00 00 00 00","00 00 00 00","00 00 00 00","00 00 00 00"], -- line 7
	["00 00 00 00","00 00 00 00","00 00 00 00","00 00 00 00"]  -- line 8
] -- end of pattern
```

In the new format, each line can have a different amount of tracks, and it'll all be padded out accordingly. If there's an old .usf file that you want converted, use the **format.py** tool. It can also take converted files and make them more readable by making tracks even across patterns, or padding out each line, making space for optional commands.

Each pattern and track can have its own length. If each track has a different length, the longest track will be used to decide the length of the pattern, and any shorter tracks will be padded out to match the length. You can have as little or as many tracks as you like in a pattern. As tracks aren't named, a way to tell which is which is by observing the sample numbers in each one. That should give you a pretty good indicator.

**"format"** - Which pattern format to use. If this is left out or set to 0, the original, per-track format is used. If set to 1, the new, readable format is used.

**"arrangement"** - List of patterns to play.

**"sample_rate"** - Sample rate at which to play the rendered file

**"beat_length"** - Length of each beat in samples. This is basically the tempo adjustment!


## Patterns, Tracks, Lines and Commands

The Unrefined format handles patterns very similarly to trackers, in that each pattern contains some amount of tracks, and each of those tracks contains various "lines" which are the commands that make things sound. These patterns can then be chained together into an arrangement. 

Each track is monophonic, in that it can only play one sample at a time. But it can play any sample, which means if you're clever enough, you can make it sound like you've got more tracks! This technique was pioneered by chiptune artists, because the sound chips in older systems could only handle so many channels of audio. Here's an example: have your bass drum, hi hat and snare on the same track. You've already saved 3 tracks!

Here's an example "line":

```05 02 3f 00 r```

...but what do those numbers mean?

**05** is the sample number to be played. You can figure these out by reading the sample list at the top and counting manually, because that's just how it works. If you want to cut the sample that's currently playing, use **--**.

**02** is a special command, in that it can tell the sample to play either faster, or slower. It's possible to change the speed of a sample while it's playing. If the first nibble is 0, then the sample will be played back slowly, and the second nibble controls the speed. If the first nibble is anything other than 0, the sample will play back quickly and the first nibble will control the speed, so the second nibble will be ignored. Playing samples faster or slower is achieved by skipping or repeating bytes of the sample. For example, to play a sample at half the speed, we repeat the current byte twice. To play it at double the speed, we skip every second byte. In the case of "02", it will skip every 3rd byte of the sample, because 00 will play the sample at its normal speed, so we count from 1. If you want to play a tune with a sample, make sure your sample is at least half the speed by default, so you've got more room to speed the sample up.

**3f** is the offset to start playing the sample from * 255. I'm quite proud of this one, as it allows for chippy choppy breakbeats and vocals to be achieved with ease. If you're doing lots of choppage, it's best to have each chop as its own sample, as sequential numbers are a lot easier to remember than 3f, 40, 5a etc. Unless you've got a good memory, of course. Note that the offset can be FF and still have some of the sample left to play. In this case, you can split the sample up using the truncate program, and use that to continue.

**00** actually doubles as two commands! The first byte delays the sample by a certain amount before playing. The adjustment is extremely fine, as the highest value (F) is the full resolution of the song, so using that is equivalent to placing a sample on the next line. The second byte controls how much the volume is reduced. This can be changed while a sample's playing, and is great for achieving echo and fade-out effects. For example, 01 will play the sample at half the volume, 02 will play it at a third of the volume, etc. It's achieved using bit shifting so the reduction in volume is consistent. If I were to use division (which is what I did originally), the reduction would be gradual yet apparent when using low values, but as the values get higher, the difference in volume would become negligible.

**r** is an optional command, and it reverses the currently playing sample. If a sample is triggered alongside an "r", it'll start playing the sample from the end. If an "r" is used on its own, it reverses the sample from its current point. Offset commands will still work, but it'll offset the sample from the end instead of the start.

Note that all hex values and optional commands are case insensitive, so you can put 0f, 0F, fD or Fd and it'll all work.

## Tips

- If you want to pitch your sample around to something more tuneful, increase the sample rate of the song (perhaps to a multiple of the current one?) and increase the beat length alongside it; for instance, multiply them both by 2, and then slow the samples down to pitch them. Alternatively, increase the range of a sample using the "speed.py" program by slowing it down. Remember that the range is limited to 16 steps up or down.
- Slowed down a sample, and you're not happy with the aliasing? Use "lowpass.py" to smoothen off the top end. A few passes are usually recommended for this purpose. Using the --accurate/-a option generally gives better results, but it never hurts to experiment!
- To calculate the beat length of a song based off a phrase sample, divide the length of it in bytes by the resolution you want your song to be (for instance, for 1/16th notes, divide it by 16). If the result is a decimal, round it down; having a sample a bit too fast is better than it being too slow, but with sample-based accuracy it's hard to tell!
- Unless you've noted it somewhere or happen to remember it, the sample rate of a sample might not match that of your song. The difference in speed could become a happy accident, and spark creativity for new ideas! Try mixing and matching samples with different rates and see what you come up with.
- When arranging a full song, make the arrangement consist of only the pattern you're working on. This'll speed up rendering times greatly, and means that you'll only hear the bit you need to. Also, for even more time-saving, use the --quality/-q option when running "unrefined.py", for instance "unrefined.py whatever.usf -q 1" to render at half quality, -q 2 to render at a third of the quality, -q 3 to render at quarter the quality, etc.
- If you're making a song and you've got a bunch of phrase samples (such as breakbeats), I strongly recommend importing them all into a piece of software like Audacity, and changing the speed so they're all the same length, then exporting. They'll sync up properly when arranging the song, and if you're doing any choppage, it means you can use the same offsets for all samples!
- If you want to do the opposite of time-stretching (time-squishing?), slow down the sample first, then stretch the result. This also doubles as a fine-tuning feature, useful if you're trying to get phrase samples in time.
- If you're making a song with a specific set of samples (ssssss), it's ideal to have all samples at the exact same sample rate so they stay in time, although one-shot sounds shouldn't be too badly affected.

## Remarks

- The replayer can be quite slow, especially with files containing multiple tracks, or files that are just long. I've tried my very hardest to optimize it, and it's already 5x faster than the first version! If you want to speed up rendering times (e.g. if you have a slower computer), try using the --quality/-q option when rendering.
- If you've rendered a file in stereo mode and the channels seem to swap during playback, that's probably a bug with PyAudio and not with the replayer. Playing the exported file in any other media player will work just fine.
- The timing of songs rendered in this format is hands down *THE* tightest you'll ever hear. Tight to the sample. You won't get any tighter than this. That's one of the main reasons I used "beat length" instead of beats per minute; you can be extremely precise, and there's no rounding going on, so you get rock solid timing every time. (ing)
- Here's a list of things that WON'T be added:
	- Chromatic pitching - This is far beyond the scope of this project, which is one-shot and phrase sampling. Have some fun with the weirdly chromatic byte skipping instead! It could give you some cool ideas.
	- Real-time playback - With the format's workflow, this isn't exactly practical. It could theoretically be possible due to the increased render speed, but with the lack of useful GUI, combined with the fact that the format's designed for one-time rendering, it may never happen.
- If rendering in 16-bit, the sound playback is extremely distorted sometimes. This is a quirk of PyAudio, and it'll sound fine in any other media player.
- Using the --safe_downsample/-sd option won't save you any time, in fact it'll take a bit longer. That's because it has to render the song in full quality first, before getting rid of any aliasing.
- 16-bit renders use double the memory (if not more), so rendering anything that either has lots of tracks, or is extremely long, will eat a huge chunk of memory, and could cause your computer to slow down. In this case, use 8-bit rendering, or use the --quality/-q option!
- Because of how the format works, if you're using a stereo sample, only the left channel will be used.

## Compatibility

- **Windows** - Perfect, because that's what it was developed on! Tested on both Windows 11 and Windows 7.
- **Linux** - Tested on Ubuntu. Requires installation of PortAudio for PyAudio to work, but once installed, works perfectly fine!
	- There may be some error messages when playing back a file, even if it plays back okay; these are caused by ALSA trying to find a bunch of devices that don't exist in the configuration file. If they're getting annoying, browse to "/usr/share/alsa/alsa.conf" and comment out all unnecessary devices, or just use the -np/--no_play option.
	- You'll need to run "python3 unrefined.py" instead of just "unrefined.py" as Linux doesn't see .py files as executable by default, though you can always change this yourself.
- **Mac** - Unknown. Please report back!

If playback is stuttering, change the "buffer_size" option in "prefs.cfg". If your song has a high sample rate, use the --safe_downsample/-sd option to guarantee less stutter. Alternatively, use --quality/-q to render at a lower sample rate; this will be quicker, but the result will include a lot more aliasing.

## Further Notes

I have included some sound utilities that allow you to affect your samples before using them in your songs, as well as a recording application that'll let you record samples on your computer in the native format! It'll even normalize and truncate your samples automatically, something that I'm extremely proud of. It uses the default device for recording, so if it's not picking up anything, check your settings. These utilities mean that you can basically construct an entire song using just the command line and a text editor!

I plan to make a GUI, but making a tracker interface is harder than I thought, and I have no idea how to approach the design. If you have any ideas or you're willing to help, don't hesitate to get in touch!

If you have any bugs or suggestions, please shoot me an e-mail @ system10@samplersonacid.com! I check my e-mails frequently, so I should(tm) respond to your message relatively quickly.

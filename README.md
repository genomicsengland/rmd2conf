# rmd2conf.py

This python 3 script allows uploading of markdown or Rmarkdown files to the Genomics England Confluence site. It was expanded from [a similar application on Github](https://github.com/RittmanMead/md_to_conf).

## Usage

`python rmd2conf.py <markdown or rmarkdownfile> -u <username> -p <password> ...`

## Arguments

  * **`-u --username`** : user's Confluence username
  * **`-p --password`** : user's Confluence password (if this contains any special characters then this will need to be within quotes)
  * **`-s --spacekey`** : the Confluence spacekey where the page will be uploaded, defaults to CDT (clinical data team)
  * **`-t --pagetitle`** : optional title for the new page upload, default is the page title specified in the Rmd or md document
  * **`-a --ancestor`** : the ancestor page's title under which the new page will be created
  * **`-m --attachment`** : paths to any attachments to upload to the page
  * **`-c --contents`** : generate a table of contents on the resulting page
  * **`-g --nogo`** : don't open up the confluence page after generating (default is to open the page after creation)
  * **`-d --delete`** : use this page to delete the page rather than create it
  * **`-n --nossl`** : use this option to use http instead of https
  * **`-b --makebackup`** : use this option to keep the markdown created from the Rmd and associated files (default is to delete)
  
The title in the (R)markdown document (or as specified in the optional argument) will determine the name of the page on the Confluence site. If a page with that title already exists in the space, then the page will be updated with the content of the markdown document, if it doesn't a new page will be created at the site's root (or under the ancestor if that is specified).

For Rmarkdown files, the first line underneath the YAML header will become the page title (unless one is specified with the `-t` flag) since the title specified in the header doesn't actually get added to the rendered document.

## Requirements

It requires the following python packages be installed:

  sys, os, subprocess, markdown, mimetypes, codecs, re, collections, requrest, json, argparse, urllib.parse, webbrowser, datetime, shutil
  
It also requires R be installed and have the rmarkdown library installed with pandoc v1.12.3 or above, this is more recent than the version available in the repositories. More information on how to get the newer version can be [found here](https://github.com/rstudio/rmarkdown/blob/master/PANDOC.md).

Obviously you need to have a confluence username and password and have permission to create pages in the space to which you're attempting to write.

## File format

The script will determine whether the file is an Rmarkdown (.Rmd) or Markdown (.md) file based on the file extension. If converting from Rmd to md, then the output format in the Rmd header will be ignored and a markdown document will be generated with a current date and time stamp (this will be deleted unless `-b` flag is specified).

## Best results

* Usage of `kable(<data.frame>)` gets nicely formatted tables.
* Plot file names come from the chunk description (and give the hover over description) so if there are chunk descriptions they need to not have any spaces in them.

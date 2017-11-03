# rmd2conf.py

This script allows uploading of markdown or Rmarkdown files to the Genomics England Confluence site. It was expanded from [a similar application on Github]<https://github.com/RittmanMead/md_to_conf>.

## Usage

python rmd2conf.py <markdown or rmarkdownfile> -u <username> -p <password> ...

## Arguments

  * **-a --ancestor** : the ancestor page's title under which 
  * **-t --attachment** : paths to any attachments to upload to the page
  * **-c --contents** : generate a table of contents on the resulting page
  * **-g --nogo** : don't open up the confluence page after generating
  * **-d --delete** : use this page to delete the page rather than create it
  * **-n --nossl** : use this option to use http instead of https
  
The title in the markdown document will determine the name of the page on the Confluence site. If a page with that title already exists in the CDT space, then the page will be updated with the content of the markdown document, if it doesn't a new page will be created at the site's root (or under the ancestor if that is specified).

## Requirements

It requires the following python packages be installed:

  sys, os, subprocess, markdown, mimetypes, codecs, re, collections, requrest, json, argparse, urllib, webbrowser
  
It also requires R be installed and have the rmarkdown library installed with pandoc v1.12.3 or above, this is more recent than the version available in the repositories. More information on how to get the newer version can be [found here]<https://github.com/rstudio/rmarkdown/blob/master/PANDOC.md>

Obviously you need to have a confluence username and password and have permission to create pages. Currently the script just writes to the **CDT** (Clinical Data Team) space. Something to be improved in the future...

## File format

The script will determine whether the file is an Rmarkdown (.Rmd) or Markdown (.md) file based on the file extension. Rmarkdown files should have  `output: md_document` in the header.

## Best results

* Usage of `kable(<data.frame>)` gets nicely formatted tables.
* Plot file names come from the chunk description (and give the hover over description).

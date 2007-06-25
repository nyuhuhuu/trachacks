/* Trac custom stylesheet for Mentalaxis.com */


/*Theme Engine Carousel Background */
#carousel {
  background-color:#CFD8EA;  
}
      
.pagebreak {
  page-break-before: always;
}

@page {
  margin: 0.25in;
}

p {
	widows: 4;
	page-break-inside: avoid;
	page-break-before: avoid;
}

html, body {
  background: #ffffff;
  font-family: Arial, Verdana, Geneva, "Bitstream Vera Sans", Helvetica, sans-serif;
  font-size: 103%;
  margin: 0;
  padding: 0;
}

body :link, body :link:hover, body :visited {
  background: transparent no-repeat;
  color: #4444aa;
}

img {
  border: 0;
}

h1, h2, h3, h4, h5 {
  font-family: Helvetica, Arial, sans-serif;
  font-weight: normal;
  color: #555555;      
  margin-top: 25px;
  margin-bottom: 5px;
}

h1, h2 {
  font-weight: bold;
}

h1 {
  page-break-before: auto;
  font-size: 190%;  
}

h2 {
  font-size: 160%;
}

h3 {
  font-size: 130%;
}

h4 {
  font-size: 115%;
}

h1, h2, h3, h4, h5 {
  page-break-after: avoid;
}

#banner {
  /* background-image: url(<?cs var:chrome.href ?>/theme/header-bg2.png); */
  background-color: #FFFFFF;
  background-repeat: repeat-x;
  border: 0;
  border-bottom: 1px solid #999999;
  height: 95px;
  padding: 0px;
  z-index: 1;
}

#header {
  left: 35px;
  right: 35px;
  top: -20px;
  position: absolute;
}

#header h1 {
	font-size: 250%;
}

#logo {
  position: absolute;
  top: 32px;
  left: 0px;
  height: 71px;
  width: 300px;     
  z-index: 1;
}

#mainnav {
  background-color: transparent;
  background-image: none; 
  font-size: 75%; 
  margin: 0;
  padding: 0px;
  position: absolute;
  top: 100px;     
  left: 20px;
  z-index: 1;      
  border:0px;
}

#mainnav ul {
  background: none;
  display: inline;
  font-size: 100%;
  list-style: none;
  margin: 0 0 4px 1.4em;
  padding: 0;
  text-align: left;
  border: 0px;
}

#mainnav li {
  color: #3c4b7b;
  background-color: #F6F6F6;
  display: inline; 
  border: 0px;
}

#mainnav :link, #mainnav :visited {
  background: transparent;
  display: inline;
  font-family: Arial, Verdana, Geneva, "Bitstream Vera Sans", Helvetica, sans-serif;
  text-align: left;
  text-transform: none;
  width: 20em !important;
  width /**/: 20.2em;
  border: 0px;
}

#mainnav :link {
  color: #3c4b7b;
  border: 0px;
}

#mainnav :visited {
  color: #4c3b5b;
  border: 0px;
}

#mainnav :link:hover, #mainnav :visited:hover {  
  backgorund:none;
  background-color: #E0E0E0;
  color: black;
  border: 0px;
}

#mainnav .active :link, #mainnav .active :visited {
  background: transparent;
  background-color: black;
  color: white;
  border: 0px;
}

#mainnav .active :link:hover, #mainnav .active :visited:hover {     
  background: transparent;
  background-color: black;
  color: white;
  border: 0px;
}

* html #mainnav :link, * html #mainnav :visited {
  color: #4b5a6a;
}

#metanav {
  position: absolute;
  top: 80px;
  right: 0px; 
}

#main {
  font-family: Arial, Verdana, Geneva, "Bitstream Vera Sans", Helvetica, sans-serif;
  font-size: 85%;
  line-height: 1.4em;
}

#ctxtnav { margin-top: 1.6em; }

#content {
  font-family: Arial, Verdana, Geneva, "Bitstream Vera Sans", Helvetica, sans-serif;
  left: 0;
  line-height: 1.4em;     
  margin: 40px 50px 50px 50px;
  padding: 0;
  z-index: 0;
}

#content.browser {
  padding: 0 0.55em 40px 0.0em;
}

#content.browser .first {
  background: transparent no-repeat;
  border-bottom: 1px dashed #cccccc;
  color: #0000aa;
}

#content.report {
  padding: 0 0.55em 40px 0.0em;
}

#content td.report {
  background: transparent no-repeat;
  border-bottom: 1px dashed #cccccc;
  color: #0000aa;
}

#content.roadmap {
  padding: 0 0.55em 40px 0.0em;
}

#content.roadmap {
  color: #234764;
}

.roadmap h1, .roadmap h2, .roadmap h3 {
  margin: 0;
}

#content.search {
  padding: 0 0.55em 40px 0.0em;
}

#content.ticket {
  padding: 0 0.55em 40px 0.0em;
}

#content.timeline {
  padding: 0 0.55em 40px 0.0em;
}

#content.timeline em {
  color: #2D5C83;
}

#content.wiki .wikipage {
  padding: 0 0px 0px 0.0em;
}                                       

.wiki-toc {
	background-color: #F0F0F0;
	border: 1px solid #999999;
	padding: 20px;
}

#search {
  font-size: normal;
  font-weight: normal;
  height: 35px;
  padding: 0 5px 0 0;
  position: absolute;
  right: 0px;
  text-align: right;
  top: 12px;
  vertical-align: middle;
  white-space: nowrap;
  width: 40em;
  z-index: 1;
}

#search input {
  font-size: 150%;
}

#search input[id="proj-search"] {
  border: 1px solid #c4cccc;
  background-color: #ffffff;
  font-size: 120%;
  font-weight: normal;
  margin: 3px 0 0 0;
  padding: 4px;
  vertical-align: middle;
  width: 20em;
}

.buttons {
  margin-right: 0;
}

input[type="Submit"], input[type="Submit"]:hover {
  background-color: #f8f7f7;
  background-image: url(<?cs var:chrome.href ?>/theme/button-on-bg.png);
  background-repeat: no-repeat;
  border-bottom: 1px solid #999999;
  border-left: 1px solid #eeeeee;
  border-right: 1px solid #999999;
  border-top: 1px solid #eeeeee;
  color: #333333;
  font-family: "Helvetiva Neue", Arial, Verdana, Geneva, "Bitstream Vera Sans", Helvetica, sans-serif;
  font-size: 100%;
  font-weight: normal;
  margin: 3px 0.4em 0px 0.4em;
  padding: 2px 0.2em 2px 0.2em;
  text-transform: lowercase;
}

pre[class="wiki"] {
  font-family: "Andale Mono",  "Courier New", monospace;
  font-size: 90%;
  font-weight: normal;
  background-color: #DAE5F4;
  color: #000000;
  border: 5px solid #94AABF;
  padding: 10px;
  page-break-before: avoid;
}

div .wiki-toc h4 {
  font-size:200%;
  font-weight:bold;
}                               
   
table.progress td.closed { border: 0; background: #5CE05D; }
table.progress td.open { border: 0; background: #DD5243; }            
.milestone .info h2 em { color: #444; font-style: normal; }        
                       
#ticket {
  background-color: #F0F0F0;
  border: 5px solid #8498AB;
  padding: 10px; 	
}

/* Tags */
.tagcloud {
  width:400px;
}

.tagcloud a {
  text-decoration: none;
  border: none;
}

.tagcount {
  font-size: 70%;
  color: #AAAAAA;
}                      

/* TracBlog */

/* Navigation */
.postmeta h2, .postmeta hr { 
	display: none 
}

.postmeta ul { 
  font-size: 10px; 
  list-style: none; 
  margin: 0; 
  text-align: right
}
.postmeta li {
  border-right: 1px solid #d7d7d7;
  display: inline;
  padding: 0 .75em;
  white-space: nowrap;
}
.postmeta li.last { border-right: none }

.blognav {
    float: right;
    border: solid 1px;
    margin: 0.5em;
    padding: 0.1em 1em 0.1em 0.1em;
/*
    width: 400px;
    background: #dfd;
*/
}

#blognav h3 {
    padding: 0.1em;
    margin: 0.4em;
}

#blognav ul {
    margin: 0.1em;
}

#blognav li {
    font-size: 0.8em;
    padding: 0.1em;
}

.blogdocs {
    float: right;
    width: 60%;
    margin: 0.5em;
    padding: 0.1em 1em 0.1em 0.1em;
}

.blogoptions {
    float: left;
}

.updated p {
  font-size: 90%;
  font-style: italic;
  font-weight: bold;
}

div.blog {
  width: 80%;
}

/* Calendar display stuff */
div.blog-calendar {
 padding: .5em 1em;
 margin: 5px 0 2em 1em;
 float: right;
 border: 1px outset #ddc;
 background: #DFEBFF;
 font-size: 85%;
 position: relative;
}

div.blog-calendar table {
/*
 border-collapse: collapse;
*/
}

div.blog-calendar td {
 padding: .25em;
 background-color: #DFEBFF; 
}

tr.blog-calendar-current {
 background: #C7D7FF;
}

td.blog-calendar-current a {
 color: #000000;
 font-weight: bold;
}

a.blog-calendar-title {
 font-size: 100%;
 color: black;
}

caption.blog-calendar-caption {
 padding-bottom: 4px;                
}

a.missing:link, a.missing.visited, a.missing {
  background-color: #DFEBFF;
}

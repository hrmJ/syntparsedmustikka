#!/usr/bin/php
<?php
//require_once 'db_functions.php';
// Mihail Mihailov july 2010
/*****************************************************************************************************
Script for outputting xml-tagged aligned text to tmx file
*****************************************************************************************************/

//************************************************************************
//Main
if ($argc < 3){
  echo "Convert parallel xml-tagged text into tmx file\n";
  echo "Usage: $argv[0] <xml file name> <tmx file name> <first language>\n";
  echo "if no language given as first language, expectinf \"fi\" \n";
  die;
}
else
{
  $xml_name = $argv[1]; 
  $text_file_name = $argv[2];
  $firstlang = (empty($argv[3])) ? "fi" : $argv[3];
  $firstlang1 = TRUE;
 // jos kieltä ei määritetty, oletetaan ensimmäiseksi kieleksi "fi", muutoin annettu kieli
  }

/***************
if (!($outfile = fopen("test.txt", "w"))){
   echo "Can't create output file\n"; die;
   } 
*************/


if (!($logfile = fopen("log.txt", "w"))){
   echo "Can't create output file\n"; die;
   } 
   
echo "Working ...\n";
$fstring = file_get_contents($xml_name);
//$fstring = file_get_contents($text_file_name);

echo "Parsing document...";

$p = xml_parser_create();
xml_parse_into_struct($p, $fstring, $vals, $index);
$res = xml_error_string(xml_get_error_code ($p));

if ($res != 'No error')
{
echo "Error: $res\n"; 
$l = xml_get_current_line_number($p);
echo "Line: $l\n";
die;

}

xml_parser_free($p);

if (!($text = fopen($text_file_name, "w"))){
   echo "Can't create output file\n"; die;
   } 

fwrite ($text, "<?xml version=\"1.0\"?>\n");
fwrite ($text, "<tmx version=\"1.4\">\n");

foreach ($vals as $item)
    {	
    $type = $item['type'];
    $tag = strtolower($item['tag']); 
    if (!empty($item['attributes'])) 
     $attr = $item['attributes'];
    else
     $attr = null;
      
    if (!empty($item['value'])) 
    	$item_val = trim($item['value']);
    else
    	$item_val = null;
    		
	/*****************
	fwrite($outfile,  "Tag: $tag\n");
	fwrite($outfile,  "Type: $type\n");
	fwrite($outfile,  "Type: $item_val \n");
	fwrite($outfile,  "****\n");
	*********************************/

	if ($tag == 'doc' && $type == 'open')
	{
		fwrite ($text, "<body>\n");
		}
	elseif ($tag == 'doc' && $type == 'close')
	{
		fwrite($text, "</tu>\n</body>\n</tmx>\n");
		}
	elseif ($tag == 'align' && $type == 'open')
	  {
		  if ($attr['LNG'] == $firstlang && !$firstlang1)
		{
		 fwrite($text,"</tu>\n");
		 fwrite($text,"<tu>\n");
			}
		elseif ($firstlang1)
		{
			fwrite($text,"<tu>\n");
			$firstlang1 = FALSE;
			}
	fwrite($text, "<tuv xml:lang = \"{$attr['LNG']}\">\n<seg>"); 
	}
	  elseif ($tag != 's' && $tag != 'p' && $tag != 'word' && $tag != 'pm' && $tag != 'lemma' && $type == 'open')
	{
	 fwrite($text, " ($tag ");
	}
	elseif ($tag == 'align' && $type == 'close')
	   {		
		fwrite($text, "</seg>\n</tuv>\n");
   }
	elseif ($tag != 's' && $tag != 'p' && $tag != 'word' && $tag != 'pm'  && $tag != 'lemma' && $type == 'close') 
	 {
	 fwrite($text, ")");
	 } 
	elseif ($tag == 'word' && !empty($item_val))
	   fwrite($text, " $item_val");
	elseif ($tag == 'pm' && !empty($item_val))
	   fwrite($text, "$item_val");   
 }	

echo "Done\n";



?>

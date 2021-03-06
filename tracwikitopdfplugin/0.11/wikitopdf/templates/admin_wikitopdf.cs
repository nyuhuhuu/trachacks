<h2>Generate WikiToPdf</h2>

<form method="post" onsubmit="compile_pages(this);">

<fieldset>
	<legend>Book Properties</legend>
	<table>
	<tbody>
		<tr>
			<td>Title:</td>
			<td><input type="text" name="title" size="80"/></td>
		</tr>
		<tr>
			<td>Sub-title:</td>
			<td><input type="text" name="subject" size="80"/></td>
		</tr>
		<tr>
			<td>Version:</td>
			<td><input type="text" name="version" size="20" /></td>
		</tr>
		<tr>
			<td>Date:</td>
			<td><input type="text" name="date" size="20"/></td>
		</tr>
	</tbody>
	</table>
</fieldset>

<fieldset>
    <legend>Select pages</legend>
	    <table border="0" width="100%">
        <tr>
            <td align="left" colspan="2">All Pages</td>
        </tr>
        <tr>
            <td colspan="2">
                <select id="leftpages_select" name="leftpages" size="10" style="width: 100%;" multiple="multiple">
                    <?cs each:page = wikitopdf.leftpages ?>
                    <option value="<?cs var:page ?>"><?cs var:page ?></option>
                    <?cs /each ?>
                </select>
            </td>
	</tr>
	<tr>
            <td align="center" colspan="2">
                <input type="button" onclick="move_item('right', 'left')" value="/\" />
					 &nbsp;&nbsp; 
                <input type="button" onclick="move_item('left', 'right')" value="\/" />
            </td>
	</tr>	
	<tr>
            <td align="left" colspan="2">Selected Pages</td>
         </tr>
	 <tr>
	 	<td width="95%">
	                <select id="rightpages_select" name="rightpages" size="10" style="width: 100%;" multiple="multiple">
                    		<?cs each:page = wikitopdf.rightpages ?>
                    		<option value="<?cs var:page ?>"><?cs var:page ?></option>
                    		<?cs /each ?>
                	</select>
		</td>
		<td width="5%" align="center">
			<input type="button" onclick="reorder_item('right', -1)" value="/\" />
			<br><br>
			<input type="button" onclick="reorder_item('right', 1)" value="\/" />
		</td>
        </tr>
  </table>    
</fieldset>

<fieldset>
    <legend>Output Format</legend>
    <?cs each:format = wikitopdf.formats ?>
    <label><input type="radio" name="format" value="<?cs name:format ?>" <?cs if:name(format)==wikitopdf.default_format ?>checked="checked"<?cs /if ?> /><?cs var:format.name ?></label>
    <?cs /each ?>
</fieldset>

<input type="hidden" name="rightpages_all" value="" />

<div class="buttons">
    <input type="submit" name="create" value="Create" />
</div>
</form>



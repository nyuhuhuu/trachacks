<?cs include "header.cs"?>
<?cs include "macros.cs"?>

<div id="ctxtnav"></div>

<div id="content" class="revtree">

<h1>Revision Tree</h1>

<div id="settings">
 <form id="prefs" method="get" action="">
  <div class="revprops">
    <fieldset id="properties">
     <legend><span class="legend">Filters</span></legend>
     <div class="field">
      <label for="branch">Branch</label>
      <select id="branch" name="branch"><?cs each:br = revtree.branches ?>
       <option value="<?cs var:br ?>" <?cs if:revtree.branch == br 
       ?>selected="selected"<?cs /if ?>><?cs var:br ?></option><?cs
      /each ?></select>
     </div>
     <div class="field">
      <label for="author">Author</label>
      <select id="author" name="author"><?cs each:auth = revtree.authors ?>
       <option value="<?cs var:auth ?>" <?cs if:revtree.author == auth 
       ?>selected="selected"<?cs /if ?>><?cs var:auth ?></option><?cs
      /each ?></select>
     </div>
    </fieldset>
   </div>
 
   <div class="revprops">
    <fieldset id="limits">
     <legend><span class="legend">Revisions</span></legend>
     <div class="field">
      <input type="radio" id="limperiod" name="limits" value="limperiod" <?cs 
       if:revtree.limits == "limperiod" ?> checked="checked"<?cs /if ?>/>
      <label for="period">Show last </label>
      <select id="period" name="period">
       <?cs each:per = revtree.periods ?><option value="<?cs 
        var:per.value ?>" <?cs if:revtree.period == per.value 
        ?>selected="selected"<?cs /if ?>><?cs var:per.label ?></option>
        <?cs /each ?></select>
     </div>
     <div class="field">
      <input type="radio" id="limrev" name="limits" value="limrev" <?cs 
       if:revtree.limits == "limrev" ?> checked="checked"<?cs /if ?>/>
      <label for="revmin">From </label>
       <select id="revmin" name="revmin">
        <?cs each:rev = revtree.revisions ?><option value="<?cs 
        var:rev ?>" <?cs if:revtree.revmin == rev ?>selected="selected"<?cs 
        /if ?>><?cs var:rev?></option>
        <?cs /each ?></select>
      <label for="revmax">up to </label>
       <select id="revmax" name="revmax">
        <?cs each:rev = revtree.revisions ?><option value="<?cs 
        var:rev ?>" <?cs if:revtree.revmax == rev ?>selected="selected"<?cs 
        /if ?>><?cs var:rev ?></option>
        <?cs /each ?></select>
     </div>
    </fieldset>
   </div>
 
   <div class="revprops" id="treeoptions">
    <fieldset>
     <legend><span class="legend">Options</span></legend>
     <div class="field">
      <input type="hidden" name="checkbox_hideterm"/>
      <input type="checkbox" id="hideterm"
        name="hideterm" <?cs if:revtree.hideterm
        ?>checked="checked"<?cs /if ?> value="1"/><label for="hideterm">Hide 
        terminated branches</label>
     </div>
    </fieldset>
   </div>
 
   <div class="revprops" id="treestyle">
    <fieldset>
     <legend><span class="legend">Style</span></legend>
      <div class="field">
        <div>
          <input type="radio" id="compact" name="treestyle" value="compact" <?cs 
         if:revtree.treestyle == "compact" ?> checked="checked"<?cs /if ?>/>
        <label for="compact">Compact</label>
        </div>
        <div>
        <input type="radio" id="timeline" name="treestyle" value="timeline" <?cs 
          if:revtree.treestyle == "timeline" ?> checked="checked"<?cs /if ?>/>
         <label for="compact">Timeline</label>
        </div>
      </div>
      <div class="buttons">
       <input type="submit" value="Update"/>
      </div>
    </fieldset>
   </div>
 
 </form>
</div>

<script type="text/javascript">
  var limrev = document.getElementById('limrev');
  var limperiod = document.getElementById('limperiod');
  var updateActionFields = function() {
    enableControl('period', limperiod.checked);
    enableControl('revmin', limrev.checked);
    enableControl('revmax', limrev.checked);
  };
  addEvent(window, 'load', updateActionFields);
  addEvent(limperiod, 'click', updateActionFields);
  addEvent(limrev, 'click', updateActionFields);
</script>

<?cs if revtree.legend ?>
<div id="legend">
 <?cs var:revtree.legend ?>
</div>
<?cs /if ?>

<?cs if revtree.errormsg ?>
<div id="errormsg" class="error">
  <p class="message"><?cs var:revtree.errormsg ?></p>
</div>
<?cs else ?>
<div class="svg">
  <!-- Inline SVG breaks the XHTML 1.0 strict conformance
       XHTML + SVG + MathML document type does not help ... -->
  <?cs var:revtree.svg.image ?>
</div>
<?cs /if ?>
</div>

<?cs include "footer.cs"?>

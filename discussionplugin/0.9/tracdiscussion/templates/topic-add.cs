<?cs include "discussion-header.cs" ?>

<h1>Add Topic</h1>

<?cs if:args.preview ?>
  <div class="message-list">
    <div class="topic">
      <div class="header">
        <div class="subject">
          <?cs var:args.subject ?>
        </div>
        <div class="body">
          <?cs var:discussion.body ?>
        </div>
        <div class="author">
          <?cs var:discussion.author ?>
        </div>
      </div>
    </div>
  </div>
<?cs /if ?>

<form class="add_form" method="post" action="<?cs var:trac.href.discussion ?>/<?cs var:discussion.forum.id ?>">
  <fieldset>
    <legend>
       Add Topic:
    </legend>
    <div class="field">
      <label for="author">Author:</label><br/>
      <?cs if:args.author ?>
        <input type="text" name="author" value="<?cs var:args.author ?>"/><br/>
      <?cs else ?>
        <input type="text" name="author" value="<?cs var:discussion.authname ?>"/><br/>
      <?cs /if ?>
    </div>
    <div class="field">
      <label for="subject">Subject:</label><br/>
      <input type="text" name="subject" value="<?cs var:args.subject ?>"/><br/>
    </div>
    <div class="field">
      <label for="body">Body:</label><br/>
      <textarea name="body" class="wikitext" rows="10" cols="78"><?cs alt:args.body ?>Enter your message here...<?cs /alt ?></textarea><br/>
    </div>
    <div class="buttons">
      <input type="submit" name="preview" value="Preview"/>
      <input type="submit" name="submit" value="Submit"/>
      <input type="submit" name="cancel" value="Cancel"/>
      <input type="hidden" name="action" value="post-add"/>
    </div>
  </fieldset>
</form>

<?cs include "discussion-footer.cs" ?>
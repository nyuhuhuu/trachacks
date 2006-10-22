<?cs include "header.cs" ?>
<?cs include "macros.cs" ?>

<div id="ctxtnav" class="nav"></div>

<div id="content" class="attachment">

<?cs if:attachment.mode == 'new' ?>
 <h1>Joindre un fichier à <a href="<?cs var:attachment.parent.href?>"><?cs
   var:attachment.parent.name ?></a></h1>
 <form id="attachment" method="post" enctype="multipart/form-data" action="">
  <div class="field">
   <label>Fichier:<br /><input type="file" name="attachment" /></label>
  </div>
  <fieldset>
   <legend>Info sur le fichier</legend>
   <?cs if:trac.authname == "anonymous" ?>
    <div class="field">
     <label>Your email or username:<br />
     <input type="text" name="author" size="30" value="<?cs
       var:attachment.author?>" /></label>
    </div>
   <?cs /if ?>
   <div class="field">
    <label>Description (optionnelle) du fichier:<br />
    <input type="text" name="description" size="60" /></label>
   </div>
   <br />
   <div class="options">
    <label><input type="checkbox" name="replace" />
    Remplacer une pièce jointe existante portant le même nom</label>
   </div>
   <br />
  </fieldset>
  <div class="buttons">
   <input type="hidden" name="action" value="new" />
   <input type="hidden" name="type" value="<?cs var:attachment.parent.type ?>" />
   <input type="hidden" name="id" value="<?cs var:attachment.parent.id ?>" />
   <input type="submit" value="Joindre" />
   <input type="submit" name="cancel" value="Annuler" />
  </div>
 </form>
<?cs elif:attachment.mode == 'delete' ?>
 <h1><a href="<?cs var:attachment.parent.href ?>"><?cs
   var:attachment.parent.name ?></a>: <?cs var:attachment.filename ?></h1>
 <p><strong>Etes-vous sûr de supprimer ce fichier</strong><br />
 Cette opération est irréversible.</p>
 <div class="buttons">
  <form method="post" action=""><div id="delete">
   <input type="hidden" name="action" value="delete" />
   <input type="submit" name="cancel" value="Annuler" />
   <input type="submit" value="Supprimer le fichier" />
  </div></form>
 </div>
<?cs elif:attachment.mode == 'list' ?>
 <h1><a href="<?cs var:attachment.parent.href ?>"><?cs
   var:attachment.parent.name ?></a></h1><?cs
  call:list_of_attachments(attachment.list, attachment.attach_href) ?>
<?cs else ?>
 <h1><a href="<?cs var:attachment.parent.href ?>"><?cs
   var:attachment.parent.name ?></a>: <?cs var:attachment.filename ?></h1>
 <table id="info" summary="Description"><tbody><tr>
   <th scope="col">
    File <?cs var:attachment.filename ?>, <?cs var:attachment.size ?> 
    (added by <?cs var:attachment.author ?>,  <?cs var:attachment.age ?> ago)
   </th></tr><tr>
   <td class="message"><?cs var:attachment.description ?></td>
  </tr>
 </tbody></table>
 <div id="preview"><?cs
  if:attachment.preview ?>
   <?cs var:attachment.preview ?><?cs
  elif:attachment.max_file_size_reached ?>
   <strong>Prévisualisation HTML impossible</strong>, car la taille du fichier 
   dépasse <?cs var:attachment.max_file_size  ?> octets. En revanche, vous 
   pouvez <a href="<?cs var:attachment.raw_href ?>">télécharger</a> le fichier.
   <?cs else ?>
   <strong>Prévisualisation HTML impossible</strong>. Pour voir son contenu,
   <a href="<?cs var:attachment.raw_href ?>">télécharge le fichier</a>.<?cs
  /if ?>
 </div>
 <?cs if:attachment.can_delete ?><div class="buttons">
  <form method="get" action=""><div id="delete">
   <input type="hidden" name="action" value="delete" />
   <input type="submit" value="Supprimer le fichier" />
  </div></form>
 </div><?cs /if ?>
<?cs /if ?>

</div>
<?cs include "footer.cs"?>

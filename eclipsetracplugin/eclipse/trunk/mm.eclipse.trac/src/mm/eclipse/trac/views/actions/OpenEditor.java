/**
 * 
 */
package mm.eclipse.trac.views.actions;

import mm.eclipse.trac.Log;
import mm.eclipse.trac.editors.WikiEditorInput;
import mm.eclipse.trac.models.WikiPage;

import org.eclipse.jface.action.Action;
import org.eclipse.jface.viewers.ISelection;
import org.eclipse.jface.viewers.IStructuredSelection;
import org.eclipse.jface.viewers.StructuredViewer;
import org.eclipse.swt.SWT;
import org.eclipse.ui.IWorkbenchPage;
import org.eclipse.ui.IWorkbenchWindow;
import org.eclipse.ui.PartInitException;
import org.eclipse.ui.PlatformUI;
import org.eclipse.ui.ide.IDE;

/**
 * @author Matteo Merli
 * 
 */
public class OpenEditor extends Action
{
    StructuredViewer viewer;
    
    public OpenEditor( StructuredViewer viewer )
    {
        this.viewer = viewer;
        setText( "Open" );
        setToolTipText( "Open wiki page in editor." );
        setAccelerator( SWT.F3 );
    }
    
    public void run()
    {
        ISelection selection = viewer.getSelection();
        Object obj = ((IStructuredSelection) selection).getFirstElement();
        
        if ( obj instanceof WikiPage )
        {
            WikiPage page = (WikiPage) obj;
            
            WikiEditorInput wikiEditorInput = new WikiEditorInput( page );
            
            IWorkbenchWindow window = PlatformUI.getWorkbench()
                    .getActiveWorkbenchWindow();
            IWorkbenchPage workbenchPage = window.getActivePage();
            
            try
            {
                IDE.openEditor( workbenchPage, wikiEditorInput,
                        "mm.eclipse.trac.editors.WikiEditor" );
            } catch ( PartInitException e )
            {
                Log.error( "Error opening wiki editor.", e );
                return;
            }
            
        } else
        {
            Log.error( "Unknown resource: " + obj );
        }
    }
}

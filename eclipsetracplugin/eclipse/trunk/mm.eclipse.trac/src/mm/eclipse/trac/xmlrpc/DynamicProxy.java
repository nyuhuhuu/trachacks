package mm.eclipse.trac.xmlrpc;

import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

import org.apache.xmlrpc.client.XmlRpcClient;
import org.apache.xmlrpc.common.TypeConverter;
import org.apache.xmlrpc.common.TypeConverterFactory;
import org.apache.xmlrpc.common.TypeConverterFactoryImpl;

public class DynamicProxy
{
    
    private final XmlRpcClient         client;
    private final TypeConverterFactory typeConverterFactory;
    private boolean                    objectMethodLocal;
    
    /**
     * Creates a new instance.
     * 
     * @param client
     *            A fully configured XML-RPC client, which is used internally to
     *            perform XML-RPC calls.
     * @param typeConverterFactory
     *            Creates instances of {@link TypeConverterFactory}, which are
     *            used to transform the result object in its target
     *            representation.
     */
    public DynamicProxy( XmlRpcClient client,
            TypeConverterFactory typeConverterFactory )
    {
        this.typeConverterFactory = typeConverterFactory;
        this.client = client;
    }
    
    /**
     * Creates a new instance. Shortcut for
     * 
     * <pre>
     * new ClientFactory( pClient, new TypeConverterFactoryImpl() );
     * </pre>
     * 
     * @param client
     *            A fully configured XML-RPC client, which is used internally to
     *            perform XML-RPC calls.
     * @see TypeConverterFactoryImpl
     */
    public DynamicProxy( XmlRpcClient client )
    {
        this( client, new TypeConverterFactoryImpl() );
    }
    
    /**
     * Returns the factories client.
     */
    public XmlRpcClient getClient()
    {
        return client;
    }
    
    /**
     * Returns, whether a method declared by the {@link Object Object class} is
     * performed by the local object, rather than by the server. Defaults to
     * true.
     */
    public boolean isObjectMethodLocal()
    {
        return objectMethodLocal;
    }
    
    /**
     * Sets, whether a method declared by the {@link Object Object class} is
     * performed by the local object, rather than by the server. Defaults to
     * true.
     */
    public void setObjectMethodLocal( boolean objectMethodLocal )
    {
        this.objectMethodLocal = objectMethodLocal;
    }
    
    /**
     * Creates an object, which is implementing the given interface. The objects
     * methods are internally calling an XML-RPC server by using the factories
     * client.
     */
    public Object newInstance( Class clazz )
    {
        return newInstance( Thread.currentThread().getContextClassLoader(),
                clazz );
    }
    
    /**
     * Creates an object, which is implementing the given interface. The objects
     * methods are internally calling an XML-RPC server by using the factories
     * client.
     */
    public Object newInstance( ClassLoader classLoader, final Class clazz )
    {
        return Proxy.newProxyInstance( classLoader, new Class[] { clazz },
                new InvocationHandler() {
                    public Object invoke( Object proxy, Method method,
                            Object[] args ) throws Throwable
                    {
                        if ( isObjectMethodLocal()
                                && method.getDeclaringClass().equals(
                                        Object.class ) ) { return method
                                .invoke( proxy, args ); }
                        String methodName = clazz.getSimpleName()
                                .toLowerCase()
                                + "." + method.getName();
                        Object result = client.execute( methodName, args );
                        TypeConverter typeConverter = typeConverterFactory
                                .getTypeConverter( method.getReturnType() );
                        return typeConverter.convert( result );
                    }
                } );
    }
}

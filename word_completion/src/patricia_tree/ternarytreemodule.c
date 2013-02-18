/*
 * ternarytreemodule.c
 * This file is part of <patricia-tree>
 *
 * Copyright (C) 2010 - Markon
 *
 * <program name> is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * <program name> is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with <program name>; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, 
 * Boston, MA  02110-1301  USA
 */


/* 
 * Ternary search tree implementation. 
 * Check on wikipedia for more info: http://en.wikipedia.org/wiki/Trie  
 */

#include <Python.h>
#include <structmember.h>
#include "ternarytreemodule.h"

/* 
 * A trie contains a root (in this case a string), a 
 * smaller, a larger and a child node that we must
 * explore to get the correct position when we insert/search.
 * 
*/

/* Forward declaration */
static PyTypeObject trieNode_Type;


/*
 * This is the allocator callback associated to the object. 
 * It doesn't initialize the object, but it just allocates enough memory for it.
 * You need to call the constructor to initialize its fields with 
 * not-None values.
*/
static PyObject *
trieNode_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    trieNode * self;
    self = (trieNode *)type->tp_alloc(type, 0);
    if(self != NULL)
    {
        Py_INCREF(Py_None);
        self->smaller = (trieNode *) Py_None;
        Py_INCREF(Py_None);
        self->larger =  (trieNode *) Py_None;
        Py_INCREF(Py_None);
        self->child = (trieNode *) Py_None;
        Py_INCREF(Py_None);
        self->c = (PyObject *) Py_None;
        Py_INCREF(Py_None);
        self->is_word = (PyObject *) Py_None;
    }
    
    return (PyObject *)self;
}

/* 
 * This is the constructor: you should call this after you've allocated 
 * enough memory for a trieNode object.
 * It takes five arguments.
 * - character: represents a char/string - is mandatory.
 * 
 * Optional arguments:
 * - word: set True or False meaning that the node represents the last 
 *   character of a word, or if it contains a single word.
 * - smaller: a smaller (according to a lexicographical order)  node
 * - larger: as above, but for larger nodes
 * - child: parent's child, containing a char/string.
 * 
*/
static int
trieNode_init(trieNode * self, PyObject * args, PyObject *kwds)
{
    PyObject *smaller= NULL, *larger= NULL, *child=NULL, *is_word=NULL, *tmp;
    PyObject *c = NULL;

    static char *kwlist[] = {"character", "word", "smaller", "larger", 
                             "child", NULL};
    if(! PyArg_ParseTupleAndKeywords(args, kwds, "S|OOOO", kwlist, 
                                    &c, &is_word, &smaller, &larger, &child))
        return -1;

    tmp = (PyObject *) self->c;
    Py_INCREF(c);
    self->c = c;
    Py_DECREF(tmp);
    if(is_word)
    {
        if (!PyBool_Check(is_word)) {
            PyErr_SetString(PyExc_TypeError, "word must be a Bool");
            return -1;
        }

        tmp = self->is_word;
        Py_INCREF(is_word);
        self->is_word = is_word;
        Py_DECREF(tmp);
    }
    else
    {
        tmp = self->is_word;
        Py_INCREF(Py_False);
        self->is_word = Py_False;
        Py_DECREF(tmp);
    }

    if(smaller)
    {
        if (!PyObject_TypeCheck(smaller, &trieNode_Type)) {
            PyErr_SetString(PyExc_TypeError, "smaller must be a TrieNode");
            return -1;
        }

        tmp = (PyObject *) self->smaller;
        Py_INCREF(smaller);
        self->smaller = (trieNode *) smaller;
        Py_DECREF(tmp);
    }
    
    if(larger)
    {
        if (!PyObject_TypeCheck(larger, &trieNode_Type)) {
            PyErr_SetString(PyExc_TypeError, "larger must be a TrieNode");
            return -1;
        }
        tmp = (PyObject *) self->larger;
        Py_INCREF(larger);
        self->larger = (trieNode *) larger;
        Py_DECREF(tmp);
    }

    if(child)
    {
        if (!PyObject_TypeCheck(child, &trieNode_Type)) {
            PyErr_SetString(PyExc_TypeError, "child must be a TrieNode");
            return -1;
        }
        tmp = (PyObject *)self->child;
        Py_INCREF(child);
        self->child = (trieNode *) child;
        Py_DECREF(tmp);
    }
    return 0;
}

/* 
 * Traverse callback: Check on the python reference for its usage.
 */
static int 
trieNode_traverse(trieNode *self, visitproc visit, void *arg)
{
    Py_VISIT(self->c);
    Py_VISIT(self->child);
    Py_VISIT(self->smaller);
    Py_VISIT(self->larger);
    Py_VISIT(self->is_word);
    return 0;
}

/* 
 * Clear callback: Check on the python reference for its usage.
 */
static int 
trieNode_clear(trieNode *self)
{
    Py_CLEAR(self->c);
    Py_CLEAR(self->child);
    Py_CLEAR(self->smaller);
    Py_CLEAR(self->larger);
    Py_CLEAR(self->is_word);
    return 0;
}


/* 
 * The deallocator callback associated to the object 
 */
static void 
trieNode_dealloc(trieNode * self)
{
    trieNode_clear(self);
    self->ob_type->tp_free((PyObject*)self);
}

/*
 * Return the char/string stored in the node
 */
static PyObject *
trieNode_get_char(trieNode * self, void *closure)
{
    Py_INCREF(self->c);
    return self->c;
}

/*
 * Set a char/string for the node
 */
static int
trieNode_set_char(trieNode * self, PyObject *value, void *closure)
{
    if(value == NULL)
    {
        PyErr_SetString(PyExc_TypeError, "Cannot delete the character attribute");
        return -1;
    }

    if (! PyUnicode_Check(value) ) {
        PyErr_SetString(PyExc_TypeError, 
                        "The value must be unicode");
        return -1;
    }
    Py_DECREF(self->c);
    Py_INCREF(value);
    self->c = value;
    return 0;
}

/*
 * Return the child stored in a node
*/
static PyObject *
trieNode_get_child(trieNode * self, void * closure)
{
    Py_INCREF(self->child);
    return (PyObject *) self->child;
}

/*
 * Set a child for the node
 */
static int
trieNode_set_child(trieNode * self, PyObject *value, void *closure)
{
    PyObject * tmp = value;
    if (value == NULL)
    {
        Py_INCREF(Py_None);
        tmp = Py_None;
    }

    if (tmp != Py_None)
    {
        if (! PyObject_TypeCheck(tmp, &trieNode_Type)) {
            PyErr_SetString(PyExc_TypeError, 
                            "The first attribute value must be a string");
            return -1;
        }
    }
    Py_DECREF(self->child);
    Py_XINCREF(tmp);
    self->child = (trieNode *) tmp;
    return 0;
}

/*
 * Return the smaller node stored in a node
 */

static PyObject *
trieNode_get_smaller(trieNode * self, void * closure)
{
    Py_INCREF(self->smaller);
    return (PyObject *) self->smaller;
}

/*
 * Set a smaller node for the node
 */
static int
trieNode_set_smaller(trieNode * self, PyObject *value, void *closure)
{
    PyObject * tmp = value;
    if (value == NULL)
    {
        Py_INCREF(Py_None);
        tmp = Py_None;
    }

    if (tmp != Py_None)
    {
        if (! PyObject_TypeCheck(tmp, &trieNode_Type)) {
            PyErr_SetString(PyExc_TypeError, 
                            "The argument must be a TrieNode");
            return -1;
        }
    }
    Py_DECREF(self->smaller);
    Py_INCREF(tmp);
    self->smaller = (trieNode *) tmp;
    return 0;

}

/*
 * Return the larger node stored in a node
 */

static PyObject *
trieNode_get_larger(trieNode * self, void * closure)
{
    Py_INCREF(self->larger);
    return (PyObject *) self->larger;
}

/*
 * Set a larger node for the node
 */


static int
trieNode_set_larger(trieNode * self, PyObject *value, void *closure)
{
    PyObject * tmp = value;
    if (value == NULL)
    {
        Py_INCREF(Py_None);
        tmp = Py_None;
    }

    if (tmp != Py_None)
    {
        if (! PyObject_TypeCheck(tmp, &trieNode_Type)) {
            PyErr_SetString(PyExc_TypeError, 
                            "The attribute must be a TrieNode");
            return -1;
        }
    }
    Py_DECREF(self->larger);
    Py_INCREF(tmp);
    self->larger = (trieNode *) tmp;
    return 0;

}
/*
 * Return True if the node has a child, False otherwise.
 */

static PyObject *
trieNode_has_child(trieNode *self)
{
    if(self->child == (trieNode *) Py_None)
    {
        Py_RETURN_FALSE;
    }
    else
        Py_RETURN_TRUE;
}

/*
 * Return True if the node is an ending word, False otherwise.
 */


static PyObject *
trieNode_is_word(trieNode *self)
{
    if(self->is_word == Py_True)
    {
        Py_RETURN_TRUE;
    }
    else
        Py_RETURN_FALSE;
}

/*
 * Set if the node is an ending word
 */
static PyObject *
trieNode_set_is_word(trieNode * self, PyObject *arg)
{
    PyObject * temp = arg;
    PyObject * old = NULL;

    if(!PyBool_Check(temp))
    {
        return NULL;
    }

    if(temp == NULL)
        return NULL;

    if (!PyBool_Check(temp)) {
            PyErr_SetString(PyExc_TypeError, "argument passed must be a Bool");
            return NULL;
    }
    old = self->is_word;
    Py_INCREF(temp);
    self->is_word = temp;
    Py_DECREF(old);
    Py_RETURN_NONE;
}

static PyGetSetDef trieNode_getseters[] = {
    {"child", (getter)trieNode_get_child, (setter)trieNode_set_child,
        "Get and set the child"},
    {"character", (getter)trieNode_get_char, (setter)trieNode_set_char, 
        "Get and set the character", NULL},
    {"smaller", (getter)trieNode_get_smaller, (setter)trieNode_set_smaller,
        "Get and set the smaller node", NULL},
    {"larger", (getter)trieNode_get_larger, (setter)trieNode_set_larger, 
        "Get and set the larger node", NULL},
    {NULL}
};

static PyMethodDef trieNode_methods[] = {
    {"has_child", (PyCFunction)trieNode_has_child, METH_NOARGS, 
        "Return true if the node has a child, false otherwise"},
    {"is_word", (PyCFunction)trieNode_is_word, METH_NOARGS, 
        "Return true if the node has a child, false otherwise"},
    {"set_word", (PyCFunction)trieNode_set_is_word, METH_O,
        "Set True if the node is an ending character, False otherwise" },
    {NULL}
};

PyDoc_STRVAR(trieNode_doc,
"TrieNode Object\n");

static PyTypeObject trieNode_Type = {
    /* The ob_type field must be initialized in the module init function
	 * to be portable to Windows without using C++. */
    PyObject_HEAD_INIT(NULL)
    0,                         /* ob_size */
    "ternarytree.TrieNodeObject", /*tp_name*/
    sizeof(trieNode),  /* tp_basicsize */
    0,                         /* tp_itemsize */
    (destructor)trieNode_dealloc,  /* tp_dealloc */
    0,                         /* tp_print */
    0,                         /* tp_getattr */
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC, /*tp_flags*/
    trieNode_doc,           /* tp_doc */
    (traverseproc)trieNode_traverse, /* tp_traverse */
    (inquiry)trieNode_clear,           /* tp_clear */
    0,                            /* tp_richcompare*/
    0,                            /* tp_weaklistoffset */
    0,                              /*tp_iter*/
    0,                              /* tp_iternext*/
    trieNode_methods,               /* tp_methods */
    0,                               /* tp_members */
    trieNode_getseters,             /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)trieNode_init,      /* tp_init */
    0,                         /* tp_alloc */
    trieNode_new,                 /* tp_new */

};

/* ============================================================
 *
 * Here we define the ternarySearchTree object and its methods 
 *
 * ============================================================
 */

/*
 * This method allocates enough memory to store a ternarySearchTree object.
 * Note that this method initialize its fields to None.
*/
static PyObject *
ternarySearchTree_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    ternarySearchTree * self;
    self = (ternarySearchTree *)type->tp_alloc(type, 0);
    if(self != NULL)
    {
        self->size = PyInt_FromLong(0);
        if (self->size == NULL)
        {
            Py_DECREF(self);
            return NULL;
        }
        
        Py_INCREF(Py_None);
        self->root = Py_None;
    }
    return (PyObject *)self;
}

/* 
 * Traverse callback. Check on the python reference for its usage.
 */
static int 
ternarySearchTree_traverse(ternarySearchTree *self, visitproc visit, void *arg)
{
    Py_VISIT(self->root);
    Py_VISIT(self->size);
    return 0;
}

/* 
 * This is the clear callback. Check on the python reference for its usage. 
 */
static int 
ternarySearchTree_clear(ternarySearchTree *self)
{
    Py_CLEAR(self->root);
    Py_CLEAR(self->size);
    return 0;
}

/*
 * The deallocator callback associated to the object 
 */
static void 
ternarySearchTree_dealloc(ternarySearchTree * self)
{
    ternarySearchTree_clear(self);
    self->ob_type->tp_free((PyObject*)self);
}

/*
 * Get the tree's size
*/
static PyObject *
ternarySearchTree_size(ternarySearchTree * self, void * closure)
{
    Py_INCREF(self->size);
    return self->size;
}

/*
 * Get the tree's root
 */
static PyObject *
ternarySearchTree_root(ternarySearchTree * self, void * closure)
{
    Py_INCREF(self->root);
    return self->root;
}

/* Forward declaration */
static PyObject *
_ternarySearchTree_insert(PyObject * node, PyObject* args);

PyDoc_STRVAR(ternarySearchTree_add_doc, 
"TernarySearchTree.add(word) -> None\n\
\n\
Try to insert the 'word' passed as argument in the tree.\n\
This method returns None\n\
Raises a ValueError if 'word' is empty.\n\
Raises a TypeError if 'word' is not a string.");

/*
 * Try to insert a new word in the tree
 * Note that now it doesn't compress the nodes. It simply insert a char 
 * in every node, even you can insert a full Python String object in the 'c' 
 * node though.
 */
static PyObject *
ternarySearchTree_add(ternarySearchTree *self, PyObject *arg)
{
    PyObject * word = arg;
    PyObject * tmp = NULL;
    PyObject * args;
    Py_ssize_t len;
    Py_XINCREF(word);

    if(!PyObject_TypeCheck(word, &PyString_Type))
    {
        return NULL;
    }

    len = PyString_GET_SIZE(word);
    if(len < 1)
    {
        PyErr_SetString(PyExc_ValueError, "word cannot be empty");
        return NULL;
    }
    args = Py_BuildValue("(Sn)", word, 0);
    if(args != NULL)
        tmp = _ternarySearchTree_insert(self->root, args);
    Py_DECREF(args);
    if(tmp == NULL)
    {
        PyObject * error = PyErr_Occurred();
        if(error != NULL)
        {
            if(PyErr_GivenExceptionMatches(error, PyExc_ValueError))
            {
                PyErr_SetString(PyExc_ValueError, "expected a string");
            }
            else if(PyErr_GivenExceptionMatches(error, PyExc_IndexError))
            {
                PyErr_SetString(PyExc_IndexError, "index out of range");
            }
            return PyErr_NoMemory();
        }
    }
    if(tmp != NULL)
    {
        self->size = PyNumber_Add(self->size, PyInt_FromLong(1));
        if(self->root == Py_None)
        {   
            Py_DECREF(self->root);
            Py_INCREF(tmp);
            self->root = tmp;
        }
    }
    Py_RETURN_NONE;
}

/*
 * An internal method used to recursively insert a word in to the tree.
 * Every object is stored as a Unicode Object
 */
static PyObject *
_ternarySearchTree_insert(PyObject * node, PyObject* args)
{   
    PyObject * c = NULL, *unicode_word = NULL, *word = NULL;
    Py_ssize_t index;
    PyObject * _args = NULL;
    int comp, recursion;
    /*
     All the references passed are borrowed, so we don't have to decrement them.
     */
    if(!PyArg_ParseTuple(args, "Sn", &word, &index))
        return NULL; 
    
    /*  we don't need to increment the reference count of word,
     *  because PyUnicode_FromEncodedObject doesn't steal the reference
     */
    unicode_word = PyUnicode_FromEncodedObject(word, "utf-8", "strict");
    if(unicode_word == NULL)
    {
        PyErr_SetString(PyExc_ValueError, "error");
        goto error;
    }

     /*Raise an exception if word is not a string/sequence */
    if(!PySequence_Check(unicode_word))
    {
        PyErr_SetString(PyExc_ValueError, "error");
        goto error;
    }
    
    // this is how we store a unicode "char"
    c = PySequence_GetItem(unicode_word, index); 
    if(c == NULL)
    {
        if(PySequence_Size(unicode_word) < index)
        {
            PyErr_SetString(PyExc_IndexError, NULL);
        }
        goto error;
    }

    if (node == Py_None)
    {
        // not initialized, but allocated
        node = trieNode_new(&trieNode_Type, NULL, NULL);
        if(node == NULL)
        {
            PyErr_SetString(PyExc_MemoryError, "memory error");
            goto error;
        }
        trieNode_set_char((trieNode *)node, c, NULL);
        
    }
    
    comp = PyUnicode_Compare(c, ((trieNode *)node)->c);
    
    if( comp == 0)
    {
        /*
         * We MUST check unicode_word's size!! 
         * If we checked PySequence_Size(word), every unicode 
         * character would have a length two times greater than a normal char, 
         * so that index would never arrive to the word's size.
         */
        if((index + 1 )  < PySequence_Size(unicode_word))
        {
            PyObject * old_child = trieNode_get_child((trieNode *)node, NULL);
            if(old_child == NULL)
                goto error;
            _args = Py_BuildValue("(Sn)", word, index+1);
            if(_args == NULL)
            {
                Py_DECREF(old_child);
                goto error;
            }
            recursion = Py_EnterRecursiveCall("insert a child node");
            PyObject * child = _ternarySearchTree_insert(old_child, _args);
            if(recursion == 0)        
                Py_LeaveRecursiveCall();
            else
            {
                Py_DECREF(old_child);
                Py_XDECREF(child);
                goto error;
            }
            Py_DECREF(old_child);
            if (child == NULL)
            {
                goto error;
            }
            trieNode_set_child((trieNode *)node, child, NULL);
            Py_DECREF(child);
            
        }
        else
        {
            trieNode_set_is_word((trieNode *) node, PyBool_FromLong(1));
        }
    }
    
    else if ( comp < 0)
    {
        PyObject * old_smaller = trieNode_get_smaller((trieNode *) node, NULL);
        if(old_smaller == NULL)
            goto error;
        _args = Py_BuildValue("(Sn)", word, index);
        if(_args == NULL)
        {
            Py_DECREF(old_smaller);
            goto error;
        }
        recursion = Py_EnterRecursiveCall("insert a smaller node");
        PyObject * smaller = _ternarySearchTree_insert(old_smaller, _args);
        if(recursion == 0)        
            Py_LeaveRecursiveCall();
        else
        {
            Py_DECREF(old_smaller);
            Py_XDECREF(smaller);
            goto error;
        }
        Py_DECREF(old_smaller);
        if (smaller == NULL)
            goto error;
        
        trieNode_set_smaller((trieNode *) node, smaller, NULL);
        Py_DECREF(smaller);
        
    }
    else if ( comp > 0)
    {
        PyObject * old_larger =  trieNode_get_larger((trieNode *) node, NULL);
        if(old_larger == NULL)
            goto error;
        _args = Py_BuildValue("(Sn)", word, index);
        if(_args == NULL)
        {
            Py_DECREF(old_larger);
            goto error;
        }
        recursion = Py_EnterRecursiveCall("insert a larger node");
        PyObject * larger = _ternarySearchTree_insert(old_larger, _args);   
        if(recursion == 0)
            Py_LeaveRecursiveCall();
        else
        {
            Py_DECREF(old_larger);
            Py_XDECREF(larger);
            goto error;
        }
        Py_DECREF(old_larger);
        if(larger == NULL)
            goto error;
        trieNode_set_larger((trieNode *) node, larger, NULL);
        Py_DECREF(larger);
    }

error:
    Py_XDECREF(c);
    Py_XDECREF(unicode_word);
    Py_XDECREF(_args);
    
    if(node == NULL)
        return NULL;

    Py_INCREF(node);
    return node;
}


/* Forward declaration */
static PyObject *
_ternarySearchTree_search(PyObject * node, PyObject *arg);

PyDoc_STRVAR(ternarySearchTree_contains_doc,
"TernarySearchTree.contains(word) -> bool\n\
\n\
Try to search the 'word' passed as argument.\n\
This method returns True if 'word' is contained in the tree.\nFalse otherwise");

/*
 * Return True if the tree contains the word passed as argument. 
 * False otherwise.
 * It uses an internal method to find every node of the word.
*/
static PyObject *
ternarySearchTree_contains(ternarySearchTree *self, PyObject *arg)
{
    PyObject * word = arg;
    PyObject * tmp = NULL;
    PyObject * args = NULL;
    Py_ssize_t len;
    if(!PyString_Check(word))
    {
        PyErr_SetString(PyExc_TypeError, "argument must be a string");
        return NULL;
    }

    len = PyString_GET_SIZE(word);
    if(len < 1)
    {
        PyErr_SetString(PyExc_ValueError, "word cannot be empty");
        return NULL;
    }
    args = Py_BuildValue("Sn", word, 0);
    if(args == NULL)
        return NULL;
    tmp = _ternarySearchTree_search(self->root, args);
    Py_DECREF(args);
    if(tmp == NULL || tmp == Py_None)        
        Py_RETURN_FALSE;
    else
    {
        PyObject * is_word = trieNode_is_word((trieNode *) tmp);
        Py_DECREF(tmp);
        return is_word;
    }
}

/* Recursive function used to look through the tree.
 * If we want to find a word, 'hello', then we 
 * first check the first character: 'h'.
 * We try to find the node containing the 'h' character in the tree, 
 * beginning from the root node.
 * If we find it, then we can check its child or siblings, 
 * and in siblings' siblings, and so on....
 * If we don't find it, then None is returned.
 */
static PyObject *
_ternarySearchTree_search(PyObject * node, PyObject *args)
{
    PyObject *word = NULL, *unicode_word=NULL, *c = NULL, *_args=NULL;
    Py_ssize_t index;
    Py_ssize_t len;
    int comp, recursion;

    if(!PyArg_ParseTuple(args, "Sn", &word, &index))
    {
        return NULL;
    }

    if(node == Py_None)
        Py_RETURN_NONE;

    unicode_word = PyUnicode_FromEncodedObject(word, "utf-8", "strict");
    len = PySequence_Size(unicode_word);
    if(unicode_word == NULL)
        goto error;

    c = PySequence_GetItem(unicode_word, index);
    Py_DECREF(unicode_word); // we don't need it anymore
    
    if(c == NULL)
    {
        if(len < index)
        {
            PyErr_SetString(PyExc_IndexError, NULL);
        }
        goto error;
    }
    
    if (node == Py_None)
        goto error;
    
    comp = PyUnicode_Compare(c, ((trieNode *)node)->c);
    
    if(comp == 0)
    {
        /* If exists at least one more character, we've to recur one more time*/
        if((index +1) < len)
        {
            PyObject * child = trieNode_get_child((trieNode *)node, NULL);
            if(child == NULL)
                goto error;
            _args = Py_BuildValue("(Sn)", word, index+1);
            if(_args == NULL)
            {
                Py_DECREF(child);
                goto error;
            }
            recursion = Py_EnterRecursiveCall("searching in a child node");
            node = _ternarySearchTree_search(child, _args);
            Py_DECREF(child);
            if(recursion == 0)        
                Py_LeaveRecursiveCall();
            else
            {
                Py_XDECREF(node);
                goto error;
            }
            if (node == NULL)
            {
                goto error;
            }
        }
    }
    else if(comp < 0)
    {
        PyObject * smaller = trieNode_get_smaller((trieNode *)node, NULL);
        if(smaller == NULL)
            goto error;
        _args = Py_BuildValue("(Sn)", word, index);
        if(_args == NULL)
        {
            Py_DECREF(smaller);
            goto error;
        }
        recursion = Py_EnterRecursiveCall("searching in a smaller node");
        node = _ternarySearchTree_search(smaller, _args);
        Py_DECREF(smaller);
        if(recursion == 0)        
            Py_LeaveRecursiveCall();
        else
        {
            Py_XDECREF(node);
            goto error;
        }
        if (node == NULL)
        {
            goto error;
        }
    }
    else
    {
            PyObject * larger = trieNode_get_larger((trieNode *)node, NULL);
            if(larger == NULL)
                goto error;
            _args = Py_BuildValue("(Sn)", word, index);
            if(_args == NULL)
            {
                Py_DECREF(larger);
                goto error;
            }
            recursion = Py_EnterRecursiveCall("searching in a larger node");
            node = _ternarySearchTree_search(larger, _args);
            Py_DECREF(larger);
            if(recursion == 0)        
                Py_LeaveRecursiveCall();
            else
            {
                Py_XDECREF(node);
                goto error;
            }
            if (node == NULL)
            {
                goto error;
            }
    }

error:
    Py_XDECREF(_args);
    if(node != NULL)
    {
        Py_INCREF(node);
    }
    return node;
}

/* Forward declaration */
static void
_ternarySearchTree_inorder_traversal(PyObject * node, PyObject *args);

PyDoc_STRVAR(ternarySearchTree_prefix_search_doc,
"TernarySearchTree.prefix_search(prefix) -> list\n\
\n\
Scan the tree to search words starting with 'prefix'.\n\
Return a new list containing the words found.");

/*
 * Scan the tree to search words starting with 'prefix'.
 * Return a new reference to a list containing the words found.
 * 
*/
static PyObject *
ternarySearchTree_prefix_search(ternarySearchTree *self, PyObject * prefix)
{
    PyObject * unicode_word=NULL, *results=NULL, *found=NULL, * _args=NULL;
    Py_ssize_t len;
    
    if(!PyString_Check(prefix))
    {
        PyErr_SetString(PyExc_TypeError, "argument must be a string");
        return NULL;
    }
    
    unicode_word = PyUnicode_FromEncodedObject(prefix, "utf-8", "strict");
    if(unicode_word == NULL)
    {
        goto error;
    }
    len = PySequence_Size(unicode_word);
    if(len < 1)
    {
        PyErr_SetString(PyExc_ValueError, "prefix cannot be an empty string");
        goto error;
    }
    
    results = PyList_New(0);
    if(results == NULL)
        goto error;
    _args = Py_BuildValue("Sn", prefix, 0);
    if(_args == NULL)
        goto error;
    found = _ternarySearchTree_search(self->root, _args);
    Py_DECREF(_args);
    // we pass a list and a unicode object as arguments
    _args = Py_BuildValue("OO", results, PySequence_GetSlice(unicode_word, 0, -1));
    if(_args == NULL)
        goto error;
    _ternarySearchTree_inorder_traversal(found, _args);
    Py_DECREF(_args);

error:
    
    Py_DECREF(unicode_word);
    if(results == NULL)
        return PyErr_NoMemory();
    return results;
}

/*
 * Internal function used to do an inorder traversal to search words
 * starting with the same prefix.
 */
static void
_ternarySearchTree_inorder_traversal(PyObject * node, PyObject *args)
{
    PyObject *results=NULL, *prefix=NULL, *sub_node = NULL, *concat=NULL;
    PyObject *unicode_word=NULL, *_args=NULL;
    int recursion;
    if(!PyArg_ParseTuple(args, "OU", &results, &prefix))
    {
        return;
    }
    if(node == Py_None)
        return;
    sub_node = trieNode_get_smaller((trieNode *)node, NULL);
    recursion = Py_EnterRecursiveCall("inorder_traversal in the smaller node");
    _ternarySearchTree_inorder_traversal(sub_node, args);
    Py_DECREF(sub_node);
    if(recursion == 0)
        Py_LeaveRecursiveCall();
    else
    {
        return;
    }
    
    // this generates a sequence, not a unicode object!
    unicode_word = trieNode_get_char((trieNode *) node, NULL);    
    if(unicode_word == NULL)
        return;
    concat = PyUnicode_Concat(prefix, unicode_word);
    if(concat == NULL)
    {
        Py_DECREF(unicode_word);
        return;
    }
    if(PyObject_IsTrue(trieNode_is_word((trieNode *)node)))
    {
        PyList_Append(results, concat);
    }
    sub_node = trieNode_get_child((trieNode *)node, NULL);
    _args = Py_BuildValue("OO", results, concat);
    Py_DECREF(concat);
    if(_args == NULL)
    {
        Py_DECREF(sub_node);
        return;;
    }
    recursion = Py_EnterRecursiveCall("inorder_traversal in the child node");
    _ternarySearchTree_inorder_traversal(sub_node, _args);
    Py_DECREF(_args);
    Py_DECREF(sub_node);
    if(recursion == 0)
        Py_LeaveRecursiveCall();
    else
        return;

    sub_node = trieNode_get_larger((trieNode *)node, NULL);
    recursion = Py_EnterRecursiveCall("inorder_traversal in the larger node");
    _ternarySearchTree_inorder_traversal(sub_node, args);
    Py_DECREF(sub_node);
    if(recursion == 0)
        Py_LeaveRecursiveCall();
    else
        return;
}

static PyMethodDef ternarySearchTree_methods[] = {
    {"add", (PyCFunction)ternarySearchTree_add, METH_O, 
                                                ternarySearchTree_add_doc},
    {"contains", (PyCFunction)ternarySearchTree_contains, METH_O, 
                                                ternarySearchTree_contains_doc},
    {"prefix_search", (PyCFunction)ternarySearchTree_prefix_search, METH_O,
                                        ternarySearchTree_prefix_search_doc},
    {NULL}
};

PyDoc_STRVAR(ternarySearchTree_size_doc, "Number of nodes stored in the tree");

static PyGetSetDef ternarySearchTree_getseters[] = {
    {"size", (getter)ternarySearchTree_size, NULL, ternarySearchTree_size_doc},
    {"root", (getter)ternarySearchTree_root, NULL, ternarySearchTree_size_doc},
    {NULL}
};

static PyTypeObject ternaryTree_Type = {
    /* The ob_type field must be initialized in the module init function
	 * to be portable to Windows without using C++. */
    PyObject_HEAD_INIT(NULL)
    0,                         /* ob_size */
    "ternarytree.TernarySearchTree", /*tp_name*/
    sizeof(ternarySearchTree),  /* tp_basicsize */
    0,                         /* tp_itemsize */
    (destructor)ternarySearchTree_dealloc,  /* tp_dealloc */
    0,                         /* tp_print */
    0,                         /* tp_getattr */
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC, /*tp_flags*/
    "Tree Node Object",           /* tp_doc */
    (traverseproc)ternarySearchTree_traverse, /* tp_traverse */
    (inquiry)ternarySearchTree_clear,           /* tp_clear */
    0,                            /* tp_richcompare*/
    0,                            /* tp_weaklistoffset */
    0,                              /*tp_iter*/
    0,                              /* tp_iternext*/
    ternarySearchTree_methods,               /* tp_methods */
    0,                                       /* tp_members */
    ternarySearchTree_getseters,             /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    0, /*(initproc)ternarySearchTree_init,       tp_init */
    0,                         /* tp_alloc */
    ternarySearchTree_new,                 /* tp_new */
};


#ifndef PyMODINIT_FUNC
#define PyMODINIT_FUNC void
#endif

PyMODINIT_FUNC
initternarytree(void)
{
    PyObject *m;
    if(PyType_Ready(&trieNode_Type) < 0)
        return;

    if(PyType_Ready(&ternaryTree_Type) < 0)
        return;

    m = Py_InitModule3("ternarytree", NULL,
                       "A CPython implementation of Ternary Search Trees.");
    Py_INCREF(&trieNode_Type);
    PyModule_AddObject(m, "TernarySearchTree", (PyObject *)&ternaryTree_Type);
}


[   [   (   1245,
            u'defect',
            1191377630,
            1191377630,
            u'component1',
            None,
            u'major',
            u'somebody',
            u'anonymous',
            u'',
            u'',
            u'',
            u'new',
            None,
            u'sum2',
            u'',
            u''),
        (   1246,
            u'task',
            1190909220,
            1190909220,
            u'',
            None,
            u'major',
            u'',
            u'testuser',
            u'',
            u'',
            u'',
            u'new',
            None,
            u'Design schematic',
            u'',
            u''),
        (   1247,
            u'task',
            1190909220,
            1190909220,
            u'',
            None,
            u'major',
            u'',
            u'testuser',
            u'',
            u'',
            u'',
            u'new',
            None,
            u'Layout board',
            u'',
            u''),
        (   1248,
            u'task',
            1190909220,
            1190909220,
            u'',
            None,
            u'major',
            u'',
            u'testuser',
            u'',
            u'',
            u'',
            u'new',
            None,
            u'Check board',
            u'',
            u''),
        (   1249,
            u'task',
            1190909220,
            1190909220,
            u'',
            None,
            u'major',
            u'',
            u'testuser',
            u'',
            u'',
            u'',
            u'new',
            None,
            u'Manufacture prototypes',
            u'',
            u''),
        (   1250,
            u'task',
            1190909220,
            1190909220,
            u'',
            None,
            u'major',
            u'',
            u'testuser',
            u'',
            u'',
            u'',
            u'new',
            None,
            u'Verify prototypes',
            u'',
            u'')],
    [   (1246, u'blockedby', u''),
        (1246, u'wbs', u''),
        (1247, u'blockedby', u'1246'),
        (1247, u'wbs', u''),
        (1248, u'blockedby', u'1247'),
        (1248, u'wbs', u'1247'),
        (1249, u'blockedby', u'1247, 1248'),
        (1249, u'wbs', u'1247'),
        (1250, u'blockedby', u'1249'),
        (1250, u'wbs', u'')],
    [   (1247, 1190909220, u'testuser', u'blockedby', u'', u'1246'),
        (1247, 1190909220, u'testuser', u'comment', u'', None),
        (1248, 1190909220, u'testuser', u'wbs', u'', u'1247'),
        (1248, 1190909220, u'testuser', u'blockedby', u'', u'1247'),
        (1248, 1190909220, u'testuser', u'comment', u'', None),
        (1249, 1190909220, u'testuser', u'wbs', u'', u'1247'),
        (1249, 1190909220, u'testuser', u'blockedby', u'', u'1247, 1248'),
        (1249, 1190909220, u'testuser', u'comment', u'', None),
        (1250, 1190909220, u'testuser', u'blockedby', u'', u'1249'),
        (1250, 1190909220, u'testuser', u'comment', u'', None)],
    [],
    []]
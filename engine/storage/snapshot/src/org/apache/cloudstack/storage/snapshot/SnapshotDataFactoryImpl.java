/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.apache.cloudstack.storage.snapshot;

import javax.inject.Inject;

import org.apache.cloudstack.engine.subsystem.api.storage.DataObject;
import org.apache.cloudstack.engine.subsystem.api.storage.DataStore;
import org.apache.cloudstack.engine.subsystem.api.storage.DataStoreManager;
import org.apache.cloudstack.engine.subsystem.api.storage.SnapshotDataFactory;
import org.apache.cloudstack.engine.subsystem.api.storage.SnapshotInfo;
import org.apache.cloudstack.engine.subsystem.api.storage.VolumeDataFactory;
import org.apache.cloudstack.storage.datastore.db.SnapshotDataStoreDao;
import org.apache.cloudstack.storage.datastore.db.SnapshotDataStoreVO;
import org.springframework.stereotype.Component;

import com.cloud.storage.DataStoreRole;
import com.cloud.storage.SnapshotVO;
import com.cloud.storage.dao.SnapshotDao;
import com.cloud.utils.exception.CloudRuntimeException;

@Component
public class SnapshotDataFactoryImpl implements SnapshotDataFactory {
    @Inject
    SnapshotDao snapshotDao;
    @Inject
    SnapshotDataStoreDao snapshotStoreDao;
    @Inject
    DataStoreManager storeMgr;
    @Inject
    VolumeDataFactory volumeFactory;

    @Override
    public SnapshotInfo getSnapshot(long snapshotId, DataStore store) {
        SnapshotVO snapshot = snapshotDao.findById(snapshotId);
        SnapshotObject so = SnapshotObject.getSnapshotObject(snapshot, store);
        return so;
    }

    @Override
    public SnapshotInfo getSnapshot(DataObject obj, DataStore store) {
        SnapshotVO snapshot = snapshotDao.findById(obj.getId());
        if (snapshot == null) {
            throw new CloudRuntimeException("Can't find snapshot: " + obj.getId());
        }
        SnapshotObject so = SnapshotObject.getSnapshotObject(snapshot, store);
        return so;
    }

    @Override
    public SnapshotInfo getSnapshot(long snapshotId, DataStoreRole role) {
        SnapshotVO snapshot = snapshotDao.findById(snapshotId);
        SnapshotDataStoreVO snapshotStore = snapshotStoreDao.findBySnapshot(snapshotId, role);
        if (snapshotStore == null) {
            return null;
        }
        DataStore store = this.storeMgr.getDataStore(snapshotStore.getDataStoreId(), role);
        SnapshotObject so = SnapshotObject.getSnapshotObject(snapshot, store);
        return so;
    }
}

import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import { StickyNote, Plus, Search, Edit3, Trash2, Save, X, Server, Cloud, Filter } from 'lucide-react';
import './Notes.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const Notes = ({ data }) => {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [cloudFilter, setCloudFilter] = useState('all');
  const [showForm, setShowForm] = useState(false);
  const [editingNote, setEditingNote] = useState(null);
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    ip_address: '',
    cloud_name: '',
    pool_name: ''
  });
  const [saving, setSaving] = useState(false);
  const formRef = useRef(null);

  const loadNotes = useCallback(async () => {
    try {
      setLoading(true);
      const params = {};
      if (cloudFilter !== 'all') params.cloud_name = cloudFilter;
      if (searchTerm) params.search = searchTerm;

      const response = await axios.get(`${API_BASE_URL}/api/notes`, { params });
      setNotes(response.data);
    } catch (err) {
      console.error('Error loading notes:', err);
    } finally {
      setLoading(false);
    }
  }, [cloudFilter, searchTerm]);

  useEffect(() => {
    loadNotes();
  }, [loadNotes]);

  const resetForm = () => {
    setFormData({ title: '', content: '', ip_address: '', cloud_name: '', pool_name: '' });
    setEditingNote(null);
    setShowForm(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.title.trim() || !formData.content.trim()) return;

    setSaving(true);
    try {
      const payload = {
        ...formData,
        ip_address: formData.ip_address || null,
        cloud_name: formData.cloud_name || null,
        pool_name: formData.pool_name || null
      };

      if (editingNote) {
        await axios.put(`${API_BASE_URL}/api/notes/${editingNote.id}`, payload);
      } else {
        await axios.post(`${API_BASE_URL}/api/notes`, payload);
      }
      resetForm();
      await loadNotes();
    } catch (err) {
      console.error('Error saving note:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (note) => {
    setFormData({
      title: note.title,
      content: note.content,
      ip_address: note.ip_address || '',
      cloud_name: note.cloud_name || '',
      pool_name: note.pool_name || ''
    });
    setEditingNote(note);
    setShowForm(true);
    setTimeout(() => formRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
  };

  const handleDelete = async (noteId) => {
    if (!window.confirm('Delete this note?')) return;
    try {
      await axios.delete(`${API_BASE_URL}/api/notes/${noteId}`);
      await loadNotes();
    } catch (err) {
      console.error('Error deleting note:', err);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleString('ru-RU', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  };

  // Get pools for selected cloud
  const getPoolsForCloud = (cloudName) => {
    if (!cloudName || !data?.clouds) return [];
    const cloud = data.clouds.find(c => c.cloud_name === cloudName);
    return cloud ? cloud.pools : [];
  };

  return (
    <div className="notes-container">
      <div className="notes-header">
        <h2>
          <StickyNote />
          Notes
        </h2>
        <button className="add-note-button" onClick={() => { resetForm(); setShowForm(true); }}>
          <Plus size={16} />
          Add Note
        </button>
      </div>

      <p className="notes-description">
        Record observations about IPs, e.g. when a public IP is attached as a secondary interface
        and not visible as occupied in the cloud.
      </p>

      <div className="notes-filters">
        <div className="search-box">
          <Search className="search-icon" />
          <input
            type="text"
            placeholder="Search notes by title, content, or IP..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
        <div className="filter-group">
          <Filter className="filter-icon" />
          <select
            value={cloudFilter}
            onChange={(e) => setCloudFilter(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Clouds</option>
            {data?.clouds?.map(cloud => (
              <option key={cloud.cloud_name} value={cloud.cloud_name}>
                {cloud.cloud_name.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
      </div>

      {showForm && (
        <div className="note-form-wrapper" ref={formRef}>
          <form className="note-form" onSubmit={handleSubmit}>
            <div className="form-header">
              <h3>{editingNote ? 'Edit Note' : 'New Note'}</h3>
              <button type="button" className="form-close" onClick={resetForm}>
                <X size={18} />
              </button>
            </div>

            <div className="form-row">
              <div className="form-field form-field-full">
                <label>Title *</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="e.g. Hidden public IP on secondary interface"
                  required
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-field">
                <label>IP Address</label>
                <input
                  type="text"
                  value={formData.ip_address}
                  onChange={(e) => setFormData({ ...formData, ip_address: e.target.value })}
                  placeholder="e.g. 176.98.235.42"
                />
              </div>
              <div className="form-field">
                <label>Cloud</label>
                <select
                  value={formData.cloud_name}
                  onChange={(e) => setFormData({ ...formData, cloud_name: e.target.value, pool_name: '' })}
                >
                  <option value="">-- Select --</option>
                  {data?.clouds?.map(cloud => (
                    <option key={cloud.cloud_name} value={cloud.cloud_name}>
                      {cloud.cloud_name.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-field">
                <label>Pool</label>
                <select
                  value={formData.pool_name}
                  onChange={(e) => setFormData({ ...formData, pool_name: e.target.value })}
                  disabled={!formData.cloud_name}
                >
                  <option value="">-- Select --</option>
                  {getPoolsForCloud(formData.cloud_name).map(pool => (
                    <option key={pool.name} value={pool.name}>{pool.name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-field form-field-full">
                <label>Content *</label>
                <textarea
                  value={formData.content}
                  onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                  placeholder="Describe the situation..."
                  rows={4}
                  required
                />
              </div>
            </div>

            <div className="form-actions">
              <button type="button" className="btn-cancel" onClick={resetForm}>Cancel</button>
              <button type="submit" className="btn-save" disabled={saving}>
                <Save size={14} />
                {saving ? 'Saving...' : editingNote ? 'Update' : 'Save'}
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="notes-loading">Loading notes...</div>
      ) : notes.length === 0 ? (
        <div className="notes-empty">
          <StickyNote size={48} />
          <p>No notes yet</p>
          <span>Add a note to record important observations about IP addresses</span>
        </div>
      ) : (
        <div className="notes-list">
          {notes.map(note => (
            <div key={note.id} className="note-card">
              <div className="note-card-header">
                <h3 className="note-title">{note.title}</h3>
                <div className="note-actions">
                  <button className="note-action-btn edit" onClick={() => handleEdit(note)} title="Edit">
                    <Edit3 size={14} />
                  </button>
                  <button className="note-action-btn delete" onClick={() => handleDelete(note.id)} title="Delete">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              <div className="note-meta">
                {note.ip_address && (
                  <span className="note-tag ip-tag">
                    <Server size={12} />
                    {note.ip_address}
                  </span>
                )}
                {note.cloud_name && (
                  <span className="note-tag cloud-tag">
                    <Cloud size={12} />
                    {note.cloud_name.toUpperCase()}
                  </span>
                )}
                {note.pool_name && (
                  <span className="note-tag pool-tag">{note.pool_name}</span>
                )}
              </div>

              <div className="note-content">{note.content}</div>

              <div className="note-footer">
                <span className="note-author">{note.author}</span>
                <span className="note-date">{formatDate(note.updated_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Notes;

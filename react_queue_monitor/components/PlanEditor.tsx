/**
 * Plan Editor Component
 * 
 * Provides interface for adding and editing plans in the queue,
 * equivalent to QtRePlanEditor in the Qt version.
 */

import React, { useState, useEffect } from 'react';
import { QueueItem, PlanInfo, DeviceInfo, PlanParameter } from '../types/queueServerTypes';

interface PlanEditorProps {
  availablePlans: PlanInfo[];
  availableDevices: DeviceInfo[];
  editingItem?: QueueItem | null;
  onAddPlan: (plan: Partial<QueueItem>, position?: number) => Promise<void>;
  onUpdatePlan: (plan: QueueItem) => Promise<void>;
  onCancel: () => void;
  visible: boolean;
}

export const PlanEditor: React.FC<PlanEditorProps> = ({
  availablePlans,
  availableDevices,
  editingItem,
  onAddPlan,
  onUpdatePlan,
  onCancel,
  visible
}) => {
  const [selectedPlan, setSelectedPlan] = useState<PlanInfo | null>(null);
  const [planArgs, setPlanArgs] = useState<any[]>([]);
  const [planKwargs, setPlanKwargs] = useState<Record<string, any>>({});
  const [planName, setPlanName] = useState<string>('');
  const [itemType, setItemType] = useState<'plan' | 'instruction'>('plan');
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Initialize form when editing an existing item
  useEffect(() => {
    if (editingItem) {
      const plan = availablePlans.find(p => p.name === editingItem.name);
      setSelectedPlan(plan || null);
      setPlanName(editingItem.name);
      setPlanArgs([...editingItem.args]);
      setPlanKwargs({ ...editingItem.kwargs });
      setItemType(editingItem.item_type);
    } else {
      resetForm();
    }
  }, [editingItem, availablePlans]);

  const resetForm = () => {
    setSelectedPlan(null);
    setPlanArgs([]);
    setPlanKwargs({});
    setPlanName('');
    setItemType('plan');
    setErrors({});
  };

  const handlePlanSelect = (planName: string) => {
    const plan = availablePlans.find(p => p.name === planName);
    if (plan) {
      setSelectedPlan(plan);
      setPlanName(plan.name);
      
      // Initialize args and kwargs based on plan parameters
      const newArgs: any[] = [];
      const newKwargs: Record<string, any> = {};
      
      plan.parameters.forEach(param => {
        if (param.kind === 'POSITIONAL_ONLY' || param.kind === 'POSITIONAL_OR_KEYWORD') {
          if (param.default === undefined) {
            newArgs.push('');
          }
        }
        if (param.kind === 'KEYWORD_ONLY' || 
           (param.kind === 'POSITIONAL_OR_KEYWORD' && param.default !== undefined)) {
          newKwargs[param.name] = param.default || '';
        }
      });
      
      setPlanArgs(newArgs);
      setPlanKwargs(newKwargs);
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    if (!planName.trim()) {
      newErrors.planName = 'Plan name is required';
    }
    
    if (selectedPlan) {
      // Validate required positional arguments
      selectedPlan.parameters.forEach((param, index) => {
        if ((param.kind === 'POSITIONAL_ONLY' || param.kind === 'POSITIONAL_OR_KEYWORD') &&
            param.default === undefined && 
            (!planArgs[index] || planArgs[index].toString().trim() === '')) {
          newErrors[`arg_${index}`] = `${param.name} is required`;
        }
      });
      
      // Validate required keyword arguments
      Object.keys(planKwargs).forEach(key => {
        const param = selectedPlan.parameters.find(p => p.name === key);
        if (param && param.default === undefined && 
            (!planKwargs[key] || planKwargs[key].toString().trim() === '')) {
          newErrors[`kwarg_${key}`] = `${key} is required`;
        }
      });
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;
    
    setLoading(true);
    try {
      const planData: Partial<QueueItem> = {
        name: planName,
        args: planArgs.map(arg => {
          // Try to parse as JSON, otherwise use as string
          if (typeof arg === 'string' && arg.trim()) {
            try {
              return JSON.parse(arg);
            } catch {
              return arg;
            }
          }
          return arg;
        }),
        kwargs: Object.fromEntries(
          Object.entries(planKwargs).map(([key, value]) => {
            if (typeof value === 'string' && value.trim()) {
              try {
                return [key, JSON.parse(value)];
              } catch {
                return [key, value];
              }
            }
            return [key, value];
          })
        ),
        item_type: itemType,
      };

      if (editingItem) {
        await onUpdatePlan({ ...editingItem, ...planData } as QueueItem);
      } else {
        await onAddPlan(planData);
      }
      
      resetForm();
      onCancel();
      
    } catch (error) {
      console.error('Failed to save plan:', error);
      alert(`Failed to save plan: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  if (!visible) return null;

  const inputStyle = {
    width: '100%',
    padding: '6px 8px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '12px'
  };

  const errorStyle = {
    color: '#dc3545',
    fontSize: '11px',
    marginTop: '2px'
  };

  return (
    <div className="plan-editor" style={{
      position: 'fixed' as const,
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        backgroundColor: '#fff',
        borderRadius: '8px',
        padding: '20px',
        width: '600px',
        maxHeight: '80vh',
        overflow: 'auto',
        boxShadow: '0 4px 20px rgba(0,0,0,0.15)'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '20px',
          borderBottom: '1px solid #eee',
          paddingBottom: '10px'
        }}>
          <h5 style={{ margin: 0, fontWeight: 'bold' }}>
            {editingItem ? 'Edit Plan' : 'Add New Plan'}
          </h5>
          <button
            onClick={onCancel}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '20px',
              cursor: 'pointer',
              color: '#6c757d'
            }}
          >
            ×
          </button>
        </div>

        {/* Plan Selection */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '4px', fontSize: '12px' }}>
            Plan:
          </label>
          <select
            value={planName}
            onChange={(e) => handlePlanSelect(e.target.value)}
            style={inputStyle}
          >
            <option value="">Select a plan...</option>
            {availablePlans.map(plan => (
              <option key={plan.name} value={plan.name}>
                {plan.name} - {plan.description || 'No description'}
              </option>
            ))}
          </select>
          {errors.planName && <div style={errorStyle}>{errors.planName}</div>}
        </div>

        {/* Item Type */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '4px', fontSize: '12px' }}>
            Type:
          </label>
          <div style={{ display: 'flex', gap: '16px' }}>
            <label style={{ display: 'flex', alignItems: 'center', fontSize: '12px', cursor: 'pointer' }}>
              <input
                type="radio"
                value="plan"
                checked={itemType === 'plan'}
                onChange={(e) => setItemType(e.target.value as 'plan')}
                style={{ marginRight: '4px' }}
              />
              Plan
            </label>
            <label style={{ display: 'flex', alignItems: 'center', fontSize: '12px', cursor: 'pointer' }}>
              <input
                type="radio"
                value="instruction"
                checked={itemType === 'instruction'}
                onChange={(e) => setItemType(e.target.value as 'instruction')}
                style={{ marginRight: '4px' }}
              />
              Instruction
            </label>
          </div>
        </div>

        {/* Plan Parameters */}
        {selectedPlan && (
          <div style={{ marginBottom: '16px' }}>
            <h6 style={{ fontWeight: 'bold', marginBottom: '12px' }}>Parameters:</h6>
            
            {/* Positional Arguments */}
            {selectedPlan.parameters
              .filter(p => p.kind === 'POSITIONAL_ONLY' || p.kind === 'POSITIONAL_OR_KEYWORD')
              .map((param, index) => (
                <div key={`arg_${index}`} style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontWeight: '500', marginBottom: '4px', fontSize: '12px' }}>
                    {param.name} {param.default === undefined && <span style={{ color: '#dc3545' }}>*</span>}
                    {param.description && (
                      <span style={{ fontWeight: 'normal', color: '#6c757d' }}>
                        {' - ' + param.description}
                      </span>
                    )}
                  </label>
                  <input
                    type="text"
                    value={planArgs[index] || ''}
                    onChange={(e) => {
                      const newArgs = [...planArgs];
                      newArgs[index] = e.target.value;
                      setPlanArgs(newArgs);
                    }}
                    placeholder={param.default !== undefined ? `Default: ${param.default}` : 'Required'}
                    style={{
                      ...inputStyle,
                      borderColor: errors[`arg_${index}`] ? '#dc3545' : '#ddd'
                    }}
                  />
                  {errors[`arg_${index}`] && <div style={errorStyle}>{errors[`arg_${index}`]}</div>}
                </div>
              ))}

            {/* Keyword Arguments */}
            {selectedPlan.parameters
              .filter(p => p.kind === 'KEYWORD_ONLY' || 
                          (p.kind === 'POSITIONAL_OR_KEYWORD' && p.default !== undefined))
              .map(param => (
                <div key={`kwarg_${param.name}`} style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontWeight: '500', marginBottom: '4px', fontSize: '12px' }}>
                    {param.name} {param.default === undefined && <span style={{ color: '#dc3545' }}>*</span>}
                    {param.description && (
                      <span style={{ fontWeight: 'normal', color: '#6c757d' }}>
                        {' - ' + param.description}
                      </span>
                    )}
                  </label>
                  <input
                    type="text"
                    value={planKwargs[param.name] || ''}
                    onChange={(e) => {
                      setPlanKwargs(prev => ({
                        ...prev,
                        [param.name]: e.target.value
                      }));
                    }}
                    placeholder={param.default !== undefined ? `Default: ${param.default}` : 'Required'}
                    style={{
                      ...inputStyle,
                      borderColor: errors[`kwarg_${param.name}`] ? '#dc3545' : '#ddd'
                    }}
                  />
                  {errors[`kwarg_${param.name}`] && <div style={errorStyle}>{errors[`kwarg_${param.name}`]}</div>}
                </div>
              ))}
          </div>
        )}

        {/* Plan Description */}
        {selectedPlan?.description && (
          <div style={{
            marginBottom: '16px',
            padding: '8px',
            backgroundColor: '#f8f9fa',
            borderRadius: '4px',
            fontSize: '12px'
          }}>
            <strong>Description:</strong> {selectedPlan.description}
          </div>
        )}

        {/* Action Buttons */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'flex-end', 
          gap: '8px',
          marginTop: '20px',
          borderTop: '1px solid #eee',
          paddingTop: '16px'
        }}>
          <button
            onClick={onCancel}
            disabled={loading}
            style={{
              padding: '8px 16px',
              fontSize: '12px',
              border: '1px solid #6c757d',
              borderRadius: '4px',
              backgroundColor: '#fff',
              color: '#6c757d',
              cursor: 'pointer'
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading || !selectedPlan}
            style={{
              padding: '8px 16px',
              fontSize: '12px',
              border: 'none',
              borderRadius: '4px',
              backgroundColor: '#007bff',
              color: '#fff',
              cursor: 'pointer',
              opacity: (loading || !selectedPlan) ? 0.6 : 1
            }}
          >
            {loading ? 'Saving...' : (editingItem ? 'Update' : 'Add to Queue')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PlanEditor;

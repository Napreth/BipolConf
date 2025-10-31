import json
from .errors import ConfigInheritPolicyError

class Config:
    """
    BipolConf configuration handler.
    Provides hierarchical namespace-based lookup with bidirectional policy inheritance.
    """
    # Load configuration immediately when class is defined
    with open('config.json', 'r', encoding='utf-8') as f:
        _config = json.load(f)

    def __init__(self, namespace: str):
        self.namespace = namespace

    @staticmethod
    def _get_policy(policies: list, allow_key: str, deny_key: str):
        # Check for conflicts
        has_allow = allow_key in policies
        has_deny = deny_key in policies
        if has_allow and has_deny:
            raise ConfigInheritPolicyError(f"Cannot configure both {allow_key} and {deny_key} simultaneously.")  # Raise error when both policies exist
        
        # Return the resolved policy
        if has_allow:
            return allow_key
        elif has_deny:
            return deny_key
        else:
            return None
        
    def _check_down_inherit(self, name, node, subnode):
        access = True
        if '__down_policies__' in self._config[node] and self._config[node]['__down_policies__']:
            policies_patterns = self._config[node]['__down_policies__']['patterns']
            policies_keys = self._config[node]['__down_policies__']['keys']
            # Retrieve policy configuration
            A1 = 'partial-inheritable-for-partial-subnode' if 'partial-inheritable-for-partial-subnode' in policies_patterns else None
            A2 = 'partial-uninheritable-for-partial-subnode' if 'partial-uninheritable-for-partial-subnode' in policies_patterns else None
            B1 = self._get_policy(policies_patterns, 'partial-inheritable', 'partial-uninheritable')
            B2 = self._get_policy(policies_patterns, 'partial-subnode-inheritable', 'partial-subnode-uninheritable')
            C = self._get_policy(policies_patterns, 'inheritable', 'uninheritable')
            if not (B1 or B2 or C): C = 'inheritable'
            if C and (B1 or B2):
                raise ConfigInheritPolicyError(f"Cannot configure global policy together with whitelist/blacklist.")
            if C:
                if C == 'uninheritable':
                    access = False
            else:
                if B1 == 'partial-inheritable':
                    if name not in policies_keys['partial-inheritable']:
                        access = False
                elif B1 == 'partial-uninheritable':
                    if name in policies_keys['partial-uninheritable']:
                        access = False
                if B2 == 'partial-subnode-inheritable':
                    if subnode not in policies_keys['partial-subnode-inheritable']:
                        access = False
                elif B2 == 'partial-subnode-uninheritable':
                    if subnode in policies_keys['partial-subnode-uninheritable']:
                        access = False
            # Exception case
            flag = 0
            if A1:
                if (name in policies_keys['partial-inheritable-for-partial-subnode'] and
                    subnode in policies_keys['partial-inheritable-for-partial-subnode'][name]):
                    access = True
                    flag += 1
            if A2:
                if (name in policies_keys['partial-uninheritable-for-partial-subnode'] and
                    subnode in policies_keys['partial-uninheritable-for-partial-subnode'][name]):
                    access = False
                    flag += 1
            if flag == 2:
                raise ConfigInheritPolicyError("Cannot define two opposite exception rules at the same time.")
        return access
    
    def _check_up_inherit(self, name, node):
        if '__up_policies__' in self._config[node] and self._config[node]['__up_policies__']['patterns']:
            policy = self._config[node]['__up_policies__']
            if len(policy['patterns']) != 1:
                raise ConfigInheritPolicyError("Only one upward inheritance policy can be defined.")
            if policy['patterns'][0] == 'uninheritable':
                raise KeyError(f"No configuration named {name} found.")
            if policy['patterns'][0] == 'partial-inheritable':
                if name not in policy['keys']['partial-inheritable']:
                    raise KeyError(f"No configuration named {name} found.")
            elif policy['patterns'][0] == 'partial-uninheritable':
                if name in policy['keys']['partial-uninheritable']:
                    raise KeyError(f"No configuration named {name} found.")

    def _iterate_node(self, node):
        subnode = ''
        while True:
            yield node, subnode
            if '.' not in node:
                break
            node, subnode = node.rsplit('.', 1)

    def __getitem__(self, name: str):
        for node, subnode in self._iterate_node(self.namespace):
            # Check whether this node exists in the configuration
            if node not in self._config: continue

            # Check whether the attribute is allowed to be inherited downward
            access = True
            if subnode:  # Check whether it is the parent instead of origin
                try:
                    access = self._check_down_inherit(name, node, subnode)
                except ConfigInheritPolicyError: raise

            # Return the configuration
            if not access:
                continue
            if name in self._config[node]:
                return self._config[node][name]
            
            # Check whether to continue querying upwards
            try:
                self._check_up_inherit(name, node)
            except (ConfigInheritPolicyError, KeyError): raise

        # Finally check the global ("*") configuration
        if '*' in self._config and name in self._config['*']:
            return self._config['*'][name]
        else:
            raise KeyError(f"No configuration named {name} found.")
